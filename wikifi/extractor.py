"""Stage 2 — per-file structured extraction.

Given the include/exclude decision from Stage 1, walk each file deterministically
and ask the LLM what intent-bearing content it contributes to each capture
section. Results are appended to per-section JSONL note files for the aggregator.

The contract: one LLM call per file *or* one call per overlapping chunk for
files that exceed the per-call window. Output is validated against a strict
Pydantic schema. Files that can't be read or validated are recorded as skipped
findings rather than crashing the walk.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from wikifi.providers.base import LLMProvider
from wikifi.sections import PRIMARY_SECTION_IDS, PRIMARY_SECTIONS
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


def extract_repo(
    *,
    layout: WikiLayout,
    provider: LLMProvider,
    files: Iterable[Path],
    repo_root: Path,
    chunk_size_bytes: int = 150_000,
    chunk_overlap_bytes: int = 8_000,
) -> ExtractionStats:
    """Walk the supplied files and append per-section findings to the notes store.

    Files larger than ``chunk_size_bytes`` are recursively split into
    overlapping chunks of at most ``chunk_size_bytes``, with
    ``chunk_overlap_bytes`` of shared context between adjacent chunks. Each
    chunk produces one LLM call; identical findings emerging from the
    overlap region are deduplicated per file so a single declaration isn't
    double-counted.
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

        chunks = _chunk_text(data, chunk_size=chunk_size_bytes, overlap=chunk_overlap_bytes)
        total_chunks = len(chunks)
        file_had_findings = False
        any_chunk_failed = False
        seen_findings: set[tuple[str, str]] = set()
        latest_summary = ""

        for chunk_index, chunk_body in enumerate(chunks):
            try:
                chunk_findings = provider.complete_json(
                    system=EXTRACTION_SYSTEM_PROMPT,
                    user=_render_user_prompt(
                        rel=rel,
                        body=chunk_body,
                        chunk_index=chunk_index,
                        total_chunks=total_chunks,
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
            if chunk_findings.summary:
                latest_summary = chunk_findings.summary

            for finding in chunk_findings.findings:
                if finding.section_id not in valid_ids:
                    continue
                key = (finding.section_id, finding.finding.strip())
                if key in seen_findings:
                    continue
                seen_findings.add(key)

                note: dict[str, object] = {
                    "file": rel.as_posix(),
                    "summary": latest_summary,
                    "finding": finding.finding,
                }
                if total_chunks > 1:
                    note["chunk"] = chunk_index
                    note["chunks"] = total_chunks
                append_note(layout, finding.section_id, note)
                stats.findings_total += 1
                file_had_findings = True

        if file_had_findings:
            stats.files_with_findings += 1
        elif any_chunk_failed and total_chunks == 1:
            # Single-call failure with no salvageable findings — count as a
            # fully skipped file, matching the pre-chunking behavior. When
            # chunked files lose some chunks we still keep what we got.
            stats.files_skipped += 1

    return stats


def _render_user_prompt(*, rel: Path, body: str, chunk_index: int = 0, total_chunks: int = 1) -> str:
    if total_chunks > 1:
        chunk_header = (
            f"Chunk: {chunk_index + 1} of {total_chunks} "
            "(adjacent chunks share an overlap region; only emit findings "
            "supported by what you see in this chunk).\n\n"
        )
    else:
        chunk_header = ""
    return (
        f"File path: {rel.as_posix()}\n\n"
        f"{chunk_header}"
        "File contents:\n"
        "```\n"
        f"{body}\n"
        "```\n\n"
        "Return findings strictly in the FileFindings schema. Use section ids "
        f"only from: {_SECTION_LIST}."
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
