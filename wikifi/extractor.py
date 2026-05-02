"""Stage 2 — per-file structured extraction.

Given the include/exclude decision from Stage 1, walk each file deterministically
and ask the LLM what intent-bearing content it contributes to each capture
section. Results are appended to per-section JSONL note files for the
aggregator.

Three orthogonal mechanisms make this stage premium-grade:

1. **Content-addressed cache.** Each file is fingerprinted; if its fingerprint
   matches a cached entry, the LLM call is skipped entirely and cached
   findings are replayed into the notes store. This is what makes a re-walk
   of a 50k-file legacy monorepo finish in minutes.
2. **Cross-file context.** A repo-wide import graph (built once, before
   extraction starts) supplies each file's neighborhood to the prompt so
   findings can describe inter-file flows.
3. **Type-aware specialization.** Files classified as SQL, OpenAPI,
   Protobuf, GraphQL, or migrations bypass the LLM entirely and run
   through deterministic extractors that read the structure directly.

Every emitted finding carries a structured :class:`SourceRef` so the
aggregator can stitch citations back into the rendered wiki.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from wikifi.cache import WalkCache
from wikifi.evidence import SourceRef
from wikifi.fingerprint import hash_file
from wikifi.providers.base import LLMProvider
from wikifi.repograph import FileKind, RepoGraph, classify
from wikifi.sections import PRIMARY_SECTION_IDS, PRIMARY_SECTIONS
from wikifi.specialized.dispatch import select as select_specialized
from wikifi.wiki import WikiLayout, append_note

log = logging.getLogger("wikifi.extractor")


# Per-file extraction targets *primary* sections only. Derivative sections
# (personas, user stories, diagrams) emerge from the aggregate of primaries
# and are produced in Stage 4 — asking the model to identify them at the
# per-file level produces sparse, speculative findings.
_SECTION_LIST = ", ".join(PRIMARY_SECTION_IDS)
_SECTION_BRIEFS = "\n".join(f"- {s.id}: {s.description}" for s in PRIMARY_SECTIONS)


EXTRACTION_SYSTEM_PROMPT = f"""\
You are wikifi's per-file extraction pass. You read a single source file and \
identify what it contributes to each section of a technology-agnostic wiki.

You describe *intent* — what the code is trying to accomplish for the system's \
users — not the mechanics of the code. Never name the language, framework, or \
library. Translate everything into domain language.

If a file contributes nothing to a section, omit that section. If a file is \
purely scaffolding (config, formatting, build, test fixtures) return an empty \
findings list.

Large files are split into overlapping chunks; you may receive one chunk at a \
time. Treat each chunk as a partial view: only emit findings supported by what \
you actually see. Adjacent chunks share an overlap region, so it is normal for \
the same finding to appear twice — that's deliberate context, not duplication \
to invent around.

When the user prompt names neighbor files (files this one imports from or is \
imported by), you may reference those relationships when describing flows that \
cross file boundaries. Do not fabricate flows that aren't visible in the chunk.

Each finding can carry an optional list of supporting line ranges within \
this file. Provide them when you can; omit them when the contribution is \
diffuse across the chunk.

Only emit findings for these section ids: {_SECTION_LIST}

Section briefs:
{_SECTION_BRIEFS}
"""


# Recursive splitter separators, ordered from "preserve the most structure"
# (paragraph breaks) down to "every byte is its own piece" (the empty
# separator). The empty separator is what guarantees a monolithic file with
# no whitespace — minified bundle, single-line JSON dump, etc. — is still
# fully consumed: it ensures the recursion always terminates with chunks
# that fit, no matter the input.
_SPLIT_SEPARATORS: tuple[str, ...] = ("\n\n", "\n", " ", "")


class SectionFinding(BaseModel):
    """A single contribution from one file to one section."""

    section_id: str = Field(description=f"Must be one of: {_SECTION_LIST}")
    finding: str = Field(description="Tech-agnostic markdown describing the contribution. 1-5 sentences.")
    line_range: tuple[int, int] | None = Field(
        default=None,
        description="Optional inclusive (start, end) line range within the chunk supporting this finding.",
    )


class FileFindings(BaseModel):
    """The full set of findings the LLM produced for a given file."""

    summary: str = Field(default="", description="One-sentence summary of the file's role.")
    findings: list[SectionFinding] = Field(default_factory=list)


@dataclass
class ExtractionStats:
    files_seen: int = 0
    files_with_findings: int = 0
    findings_total: int = 0
    files_skipped: int = 0
    chunks_processed: int = 0
    cache_hits: int = 0
    specialized_files: int = 0
    files_kinds: dict[str, int] = field(default_factory=dict)


def extract_repo(
    *,
    layout: WikiLayout,
    provider: LLMProvider,
    files: Iterable[Path],
    repo_root: Path,
    chunk_size_bytes: int = 150_000,
    chunk_overlap_bytes: int = 8_000,
    cache: WalkCache | None = None,
    graph: RepoGraph | None = None,
    persist_cache: Callable[[], None] | None = None,
    use_specialized_extractors: bool = True,
) -> ExtractionStats:
    """Walk the supplied files and append per-section findings to the notes store.

    Files larger than ``chunk_size_bytes`` are recursively split into
    overlapping chunks of at most ``chunk_size_bytes``, with
    ``chunk_overlap_bytes`` of shared context between adjacent chunks. Each
    chunk produces one LLM call; identical findings emerging from the
    overlap region are deduplicated per file so a single declaration isn't
    double-counted.

    When a ``cache`` is supplied, files whose content fingerprint matches a
    cached entry skip the LLM call entirely and replay the cached findings.
    When ``persist_cache`` is supplied, it is invoked after each file
    finishes — that turns crash-resumability into a free property of the
    cache layer.
    """
    stats = ExtractionStats()
    valid_ids = set(PRIMARY_SECTION_IDS)

    for rel in files:
        stats.files_seen += 1
        full = repo_root / rel
        try:
            data = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            log.warning("could not read %s; skipping", rel)
            stats.files_skipped += 1
            continue

        try:
            fingerprint = hash_file(full)
        except OSError:
            fingerprint = ""

        kind = classify(rel, sample=data[:4096])
        kind_label = kind.value
        stats.files_kinds[kind_label] = stats.files_kinds.get(kind_label, 0) + 1

        # ---- cache hit ----
        if cache is not None and fingerprint:
            cached = cache.lookup_extraction(rel.as_posix(), fingerprint)
            if cached is not None:
                file_had_findings = _replay_cached(layout, rel, cached, valid_ids, stats)
                if file_had_findings:
                    stats.files_with_findings += 1
                stats.cache_hits += 1
                if persist_cache is not None:
                    persist_cache()
                continue

        # ---- specialized routing ----
        specialized_fn = select_specialized(kind, rel_path=rel.as_posix()) if use_specialized_extractors else None
        if specialized_fn is not None:
            stats.specialized_files += 1
            try:
                result = specialized_fn(rel.as_posix(), data)
            except Exception as exc:  # specialized failures don't kill the walk
                log.warning("specialized extraction failed for %s: %s", rel, exc)
                stats.files_skipped += 1
                continue

            cached_findings = []
            file_had_findings = False
            for finding in result.findings:
                if finding.section_id not in valid_ids:
                    continue
                note = _build_note(
                    rel=rel,
                    summary=result.summary,
                    finding_text=finding.finding,
                    sources=finding.sources,
                    extractor=f"specialized:{kind_label}",
                )
                append_note(layout, finding.section_id, note)
                cached_findings.append(
                    {
                        "section_id": finding.section_id,
                        "finding": finding.finding,
                        "sources": [s.model_dump() for s in finding.sources],
                    }
                )
                stats.findings_total += 1
                file_had_findings = True
            if file_had_findings:
                stats.files_with_findings += 1
            if cache is not None and fingerprint:
                cache.record_extraction(
                    rel.as_posix(),
                    fingerprint=fingerprint,
                    findings=cached_findings,
                    summary=result.summary,
                    chunks_processed=0,
                )
            if persist_cache is not None:
                persist_cache()
            continue

        # ---- LLM extraction path ----
        chunks = _chunk_text(data, chunk_size=chunk_size_bytes, overlap=chunk_overlap_bytes)
        total_chunks = len(chunks)
        file_had_findings = False
        any_chunk_failed = False
        seen_findings: set[tuple[str, str]] = set()
        latest_summary = ""
        cached_findings: list[dict] = []
        chunks_done = 0

        neighbors = graph.neighbor_paths(rel.as_posix()) if graph is not None else []

        # Track each chunk's starting line so finding line_ranges can be
        # mapped back to absolute file lines for the citation.
        chunk_offsets = _chunk_line_offsets(data, chunks)

        for chunk_index, chunk_body in enumerate(chunks):
            try:
                chunk_findings = provider.complete_json(
                    system=EXTRACTION_SYSTEM_PROMPT,
                    user=_render_user_prompt(
                        rel=rel,
                        body=chunk_body,
                        chunk_index=chunk_index,
                        total_chunks=total_chunks,
                        neighbors=neighbors,
                    ),
                    schema=FileFindings,
                )
            except Exception as exc:  # provider/parse errors are per-chunk
                log.warning(
                    "extraction failed for %s (chunk %d/%d): %s",
                    rel,
                    chunk_index + 1,
                    total_chunks,
                    exc,
                )
                any_chunk_failed = True
                continue

            stats.chunks_processed += 1
            chunks_done += 1
            if chunk_findings.summary:
                latest_summary = chunk_findings.summary

            chunk_line_offset = chunk_offsets[chunk_index]
            for finding in chunk_findings.findings:
                if finding.section_id not in valid_ids:
                    continue
                key = (finding.section_id, finding.finding.strip())
                if key in seen_findings:
                    continue
                seen_findings.add(key)

                line_range: tuple[int, int] | None = None
                if finding.line_range is not None:
                    start, end = finding.line_range
                    line_range = (start + chunk_line_offset, end + chunk_line_offset)

                sources = [SourceRef(file=rel.as_posix(), lines=line_range, fingerprint=fingerprint)]
                note = _build_note(
                    rel=rel,
                    summary=latest_summary,
                    finding_text=finding.finding,
                    sources=sources,
                    extractor=f"llm:{kind_label}",
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                )
                append_note(layout, finding.section_id, note)
                cached_findings.append(
                    {
                        "section_id": finding.section_id,
                        "finding": finding.finding,
                        "sources": [s.model_dump() for s in sources],
                    }
                )
                stats.findings_total += 1
                file_had_findings = True

        if file_had_findings:
            stats.files_with_findings += 1
        elif any_chunk_failed and total_chunks == 1:
            # Single-call failure with no salvageable findings — count as a
            # fully skipped file, matching the pre-chunking behavior. When
            # chunked files lose some chunks we still keep what we got.
            stats.files_skipped += 1

        if cache is not None and fingerprint and chunks_done > 0:
            cache.record_extraction(
                rel.as_posix(),
                fingerprint=fingerprint,
                findings=cached_findings,
                summary=latest_summary,
                chunks_processed=chunks_done,
            )
        if persist_cache is not None:
            persist_cache()

    return stats


def _replay_cached(
    layout: WikiLayout,
    rel: Path,
    cached,
    valid_ids: set[str],
    stats: ExtractionStats,
) -> bool:
    """Re-emit cached findings into the notes store. Returns True if any landed."""
    file_had_findings = False
    for entry in cached.findings:
        section_id = entry.get("section_id", "")
        if section_id not in valid_ids:
            continue
        sources = [SourceRef(**s) for s in entry.get("sources", [])]
        note = _build_note(
            rel=rel,
            summary=cached.summary,
            finding_text=entry.get("finding", ""),
            sources=sources,
            extractor="cache",
        )
        append_note(layout, section_id, note)
        stats.findings_total += 1
        file_had_findings = True
    return file_had_findings


def _build_note(
    *,
    rel: Path,
    summary: str,
    finding_text: str,
    sources: list[SourceRef],
    extractor: str,
    chunk_index: int | None = None,
    total_chunks: int | None = None,
) -> dict[str, object]:
    note: dict[str, object] = {
        "file": rel.as_posix(),
        "summary": summary,
        "finding": finding_text,
        "sources": [s.model_dump() for s in sources],
        "extractor": extractor,
    }
    if total_chunks is not None and total_chunks > 1:
        note["chunk"] = chunk_index
        note["chunks"] = total_chunks
    return note


def _render_user_prompt(
    *,
    rel: Path,
    body: str,
    chunk_index: int = 0,
    total_chunks: int = 1,
    neighbors: list[str] | None = None,
) -> str:
    if total_chunks > 1:
        chunk_header = (
            f"Chunk: {chunk_index + 1} of {total_chunks} "
            "(adjacent chunks share an overlap region; only emit findings "
            "supported by what you see in this chunk).\n\n"
        )
    else:
        chunk_header = ""
    neighbor_block = ""
    if neighbors:
        neighbor_lines = "\n".join(f"  - {n}" for n in neighbors[:8])
        neighbor_block = (
            "Neighbor files (this file imports from or is imported by these — "
            "feel free to mention cross-file relationships when supported by the chunk):\n"
            f"{neighbor_lines}\n\n"
        )
    return (
        f"File path: {rel.as_posix()}\n\n"
        f"{neighbor_block}"
        f"{chunk_header}"
        "File contents:\n"
        "```\n"
        f"{body}\n"
        "```\n\n"
        "Return findings strictly in the FileFindings schema. Use section ids "
        f"only from: {_SECTION_LIST}. Provide ``line_range`` as an inclusive "
        "(start, end) pair *within this chunk* whenever the contribution is "
        "tied to a specific span; omit it for diffuse contributions."
    )


def _chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Recursively split ``text`` into chunks of at most ``chunk_size`` bytes,
    each starting with up to ``overlap`` bytes of the previous chunk for
    cross-boundary context.

    The split tries semantic separators first (blank lines, then single
    newlines, then whitespace) and resorts to byte boundaries only when none
    of those appear — so a monolithic single-line file is still fully
    consumed, while normal source code keeps clean line boundaries.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
    if len(text) <= chunk_size:
        return [text]

    base_size = chunk_size - overlap
    base_chunks = _recursive_split(text, chunk_size=base_size, separators=list(_SPLIT_SEPARATORS))
    if len(base_chunks) <= 1 or overlap == 0:
        return base_chunks

    # Prepend the tail of each previous chunk to its successor. This expands
    # each chunk by up to ``overlap`` bytes, but never beyond ``chunk_size``
    # since base_size + overlap == chunk_size.
    overlapped: list[str] = [base_chunks[0]]
    # Pairwise iteration over (prev, curr); lengths differ by one by
    # construction, so strict=False is correct.
    for prev, curr in zip(base_chunks, base_chunks[1:], strict=False):
        tail = prev[-overlap:] if len(prev) > overlap else prev
        overlapped.append(tail + curr)
    return overlapped


def _chunk_line_offsets(text: str, chunks: list[str]) -> list[int]:
    """Return the starting line number (0-indexed offset) of each chunk
    within ``text``. Used to translate per-chunk line ranges into absolute
    file line ranges for citations.
    """
    offsets: list[int] = []
    cursor = 0
    for chunk in chunks:
        idx = text.find(chunk, cursor)
        if idx < 0:
            # Overlap or aggressive splitting can shift the search window;
            # fall back to a global find. Worst case: line offsets are
            # approximate, which is acceptable for citation purposes.
            idx = text.find(chunk)
            if idx < 0:
                offsets.append(0)
                continue
        offsets.append(text.count("\n", 0, idx))
        cursor = idx + max(1, len(chunk) // 2)  # advance past most of this chunk
    return offsets


def _recursive_split(text: str, *, chunk_size: int, separators: list[str]) -> list[str]:
    """Split ``text`` so every chunk fits within ``chunk_size``, trying each
    separator in priority order. The empty-string separator is the terminal
    step: it slices at byte boundaries so the recursion always succeeds even
    on inputs with no whitespace.
    """
    if len(text) <= chunk_size:
        return [text] if text else []

    if not separators:
        # Terminal byte-boundary split — only reached if the empty-string
        # separator was somehow removed from the list.
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    sep, *rest = separators
    if sep == "":
        # Character-level split — every character is its own piece. The
        # accumulator below packs them back into chunk_size-bounded chunks.
        pieces = list(text)
    else:
        parts = text.split(sep)
        # Reattach the separator to all but the last piece so concatenation
        # reproduces the original text.
        pieces = [p + sep for p in parts[:-1]] + [parts[-1]]

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if len(piece) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_recursive_split(piece, chunk_size=chunk_size, separators=rest))
        elif len(current) + len(piece) > chunk_size:
            if current:
                chunks.append(current)
            current = piece
        else:
            current += piece
    if current:
        chunks.append(current)
    return chunks


def classify_file(rel_path: Path, sample: str) -> FileKind:
    """Public re-export so callers don't need to import :mod:`repograph`."""
    return classify(rel_path, sample=sample)
