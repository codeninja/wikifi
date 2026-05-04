"""Stage 3 — per-section synthesis.

Reads the JSONL notes accumulated by the extractor and asks the LLM to
synthesize each section's final markdown along with **structured
evidence**: a list of supported claims and any contradictions surfaced
across the file findings.

Three behaviors set this stage apart from a vanilla "merge LLM output":

1. **Citations.** Every claim records the source files (and line ranges
   when the extractor knew them) it draws from. The renderer threads
   those into the final markdown as numbered footnotes.
2. **Contradiction surfacing.** When two or more files disagree about
   the same domain claim — a frequent case in legacy systems where
   tribal knowledge hides in inconsistencies — the conflict is rendered
   under a "Conflicts in source" heading rather than silently merged.
3. **Section-level cache.** A digest of the section's note payload is
   compared against the prior walk's; if the notes are byte-identical,
   the cached body and evidence are reused without re-calling the LLM.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, Field

from wikifi.cache import WalkCache, hash_section_notes, note_finding_ids
from wikifi.evidence import (
    Claim,
    Contradiction,
    EvidenceBundle,
    SourceRef,
    coalesce_refs,
    render_section_body,
)
from wikifi.providers.base import LLMProvider
from wikifi.sections import PRIMARY_SECTIONS, Section
from wikifi.surgical import classify_section_change, surgical_aggregate
from wikifi.wiki import WikiLayout, read_notes, write_section

log = logging.getLogger("wikifi.aggregator")

AGGREGATION_SYSTEM_PROMPT = """\
You are wikifi's section aggregator. You receive structured notes that an \
extractor pass collected from individual source files in a target codebase, \
along with the brief for one section of a tech-agnostic wiki. Synthesize a \
clean markdown body for that section *and* expose the evidence you used.

Each note carries an `[index]` tag — when you make a claim that draws on \
specific notes, list those indices in the corresponding `claim.source_indices`. \
Indices are 1-based and refer to the numbered notes in the user prompt.

Rules:
- Tech-agnostic. Never mention specific languages, frameworks, or libraries. \
  Translate every observation into domain terms.
- Coherent narrative — not a transcript of the notes. Merge consistent \
  statements, organize by domain logic.
- DO NOT silently resolve contradictions. If two notes assert incompatible \
  things about the same topic, emit a `contradictions[]` entry naming each \
  position and the source-note indices that support it.
- Use markdown sub-headings, lists, and tables in `body` where they help.
- Keep `body` focused on prose; the renderer adds the citation footer and \
  "Conflicts in source" block from the structured `claims`/`contradictions` \
  fields. Don't duplicate citations inline.
- If notes are sparse or contradictory, say so plainly rather than inventing.
- Output the body only (no top-level heading); the writer adds the title.
"""


class AggregatedClaim(BaseModel):
    """One claim the aggregator extracted, indexed against the input notes."""

    text: str = Field(description="One assertion in the synthesized body.")
    source_indices: list[int] = Field(
        default_factory=list,
        description="1-based indices of the notes that justify this claim.",
    )


class AggregatedContradiction(BaseModel):
    summary: str = Field(description="One-sentence description of the disagreement.")
    positions: list[AggregatedClaim] = Field(
        default_factory=list,
        description="Each disagreeing position, with its own supporting note indices.",
    )


class SectionBody(BaseModel):
    """The aggregator's structured output for a single section."""

    body: str = Field(description="Markdown content for the section, no top-level heading.")
    claims: list[AggregatedClaim] = Field(default_factory=list)
    contradictions: list[AggregatedContradiction] = Field(default_factory=list)


@dataclass
class AggregationStats:
    sections_written: int = 0
    sections_empty: int = 0
    sections_cached: int = 0
    sections_edited: int = 0
    sections_rewritten: int = 0


def aggregate_all(
    *,
    layout: WikiLayout,
    provider: LLMProvider,
    cache: WalkCache | None = None,
    persist_cache: Callable[[], None] | None = None,
    surgical_threshold: float = 0.3,
    use_surgical_edits: bool = True,
) -> AggregationStats:
    """Aggregate every primary section from its accumulated notes.

    Derivative sections (personas, user stories, diagrams) are populated by
    `wikifi.deriver.derive_all` after this stage — they have no per-file
    notes to aggregate from.

    Each section follows one of four paths, in priority order:

    1. **Cache hit** — ``notes_hash`` matches the cached entry exactly.
       Re-render the cached bundle, no LLM call. (Plan A behavior.)
    2. **Unchanged finding set** — ``notes_hash`` differs but the
       finding ids are identical (a source line shifted, summary
       changed, etc.). Re-render the cached body, no LLM call. The
       cached ``notes_hash`` is *not* refreshed: the citations in the
       cached claims still reference the prior walk's line ranges /
       fingerprints, so a later walk needs another aggregation pass to
       refresh them. Leaving the cache key stale keeps
       :func:`aggregation_fully_cached` honest — the orchestrator's
       short-circuit will not skip stage 3 for a section whose
       citations could be drifting.
    3. **Surgical edit** — finding-set churn ratio is at or below
       ``surgical_threshold``. Send the cached body plus the added /
       removed delta to the LLM and merge the edit into the cached
       claims. Preserves prose for unchanged paragraphs.
    4. **Full rewrite** — too much churn (or no prior cached body to
       edit). Re-aggregate from scratch. (Plan A behavior.)

    Only Path 3 is gated by ``use_surgical_edits``; setting it to
    ``False`` disables the LLM-side surgical edit, leaving the three
    no-LLM paths (full cache hit, unchanged-finding-set re-render,
    and full rewrite) intact. Path 2 in particular still fires when
    only line ranges or summaries drift — that's a generic cache-reuse
    optimization not specific to surgical editing.

    When ``persist_cache`` is supplied, it is invoked after each successful
    section's cache update — that turns a Ctrl-C / OOM mid-stage-3 into a
    survivable event. Without incremental persistence, every aggregation
    cache update from this stage would be lost if anything raised before
    the orchestrator's final ``save`` at the end of the walk.
    """
    stats = AggregationStats()
    for section in PRIMARY_SECTIONS:
        notes = read_notes(layout, section)
        if not notes:
            empty_body = _empty_body(section)
            write_section(layout, section, empty_body)
            stats.sections_empty += 1
            # Record an empty-state cache entry so a subsequent walk can
            # tell "this section was aggregated against zero notes" apart
            # from "this section was never aggregated, body on disk is
            # stale." Without this, a deletion that empties a section's
            # notes would let the orchestrator's full-cache short-circuit
            # skip stage 3 while leaving the prior walk's prose in place.
            if cache is not None:
                cache.record_aggregation(
                    section.id,
                    notes_hash=hash_section_notes([]),
                    body=empty_body,
                    claims=[],
                    contradictions=[],
                )
                if persist_cache is not None:
                    persist_cache()
            continue

        notes_hash = hash_section_notes(notes)
        live_finding_ids = note_finding_ids(notes, section_id=section.id)

        # Path 1: full cache hit. Identical notes payload, identical
        # citations, identical body — re-render and move on.
        if cache is not None:
            cached_hit = cache.lookup_aggregation(section.id, notes_hash)
            if cached_hit is not None:
                bundle = EvidenceBundle(
                    body=cached_hit.body,
                    claims=[Claim.model_validate(c) for c in cached_hit.claims],
                    contradictions=[Contradiction.model_validate(c) for c in cached_hit.contradictions],
                )
                write_section(layout, section, render_section_body(bundle))
                stats.sections_cached += 1
                stats.sections_written += 1
                continue

        cached_entry = cache.aggregation.get(section.id) if cache is not None else None
        change = classify_section_change(
            cached=cached_entry,
            live_finding_ids=live_finding_ids,
            surgical_threshold=surgical_threshold if use_surgical_edits else -1.0,
        )

        # Path 2: finding ids unchanged but notes_hash differs (e.g.
        # line ranges shifted, summary changed). The cached body's
        # narrative still holds because every finding_id is still
        # present, so we re-render rather than calling the LLM.
        #
        # Deliberately *don't* refresh the cache entry here. The cached
        # ``claims`` carry resolved SourceRefs (file/lines/fingerprint)
        # captured at prior-walk extraction time; if line ranges or
        # fingerprints drifted, those refs are stale. Re-rendering with
        # them is a tolerable per-walk shortcut, but updating
        # ``notes_hash`` to match live notes would let
        # :func:`aggregation_fully_cached` flag the section as fresh
        # and the orchestrator would then skip stage 3 entirely on the
        # next no-source-change walk — locking the stale citations in
        # place. Leaving the cache key alone keeps the predicate honest
        # and lets a future Path 4 rewrite refresh citations cleanly.
        if change.decision == "unchanged" and cached_entry is not None:
            bundle = EvidenceBundle(
                body=cached_entry.body,
                claims=[Claim.model_validate(c) for c in cached_entry.claims],
                contradictions=[Contradiction.model_validate(c) for c in cached_entry.contradictions],
            )
            write_section(layout, section, render_section_body(bundle))
            stats.sections_cached += 1
            stats.sections_written += 1
            continue

        bundle: EvidenceBundle | None = None
        path_taken: str = "rewrite"

        # Path 3: surgical edit. Hand the cached body + delta to the LLM.
        # On any failure we fall through to the rewrite path so the user
        # never gets a missing section.
        if change.decision == "surgical" and cached_entry is not None:
            try:
                bundle = surgical_aggregate(
                    section=section,
                    cached=cached_entry,
                    live_notes=notes,
                    change=change,
                    provider=provider,
                )
                path_taken = "edited"
            except Exception as exc:
                log.warning(
                    "surgical edit failed for %s (%s); falling back to full rewrite",
                    section.id,
                    exc,
                )
                bundle = None

        # Path 4: full rewrite. Either the classifier said so, or the
        # surgical attempt above raised.
        if bundle is None:
            try:
                structured = provider.complete_json(
                    system=AGGREGATION_SYSTEM_PROMPT,
                    user=_render_user_prompt(section, notes),
                    schema=SectionBody,
                )
                bundle = _bundle_from(structured, notes)
                path_taken = "rewrite"
            except Exception as exc:
                log.warning("aggregation failed for %s: %s", section.id, exc)
                rendered = _fallback_body(section, notes, error=str(exc))
                write_section(layout, section, rendered)
                stats.sections_written += 1
                continue

        write_section(layout, section, render_section_body(bundle))
        stats.sections_written += 1
        if path_taken == "edited":
            stats.sections_edited += 1
        else:
            stats.sections_rewritten += 1

        if cache is not None:
            cache.record_aggregation(
                section.id,
                notes_hash=notes_hash,
                body=bundle.body,
                claims=[c.model_dump() for c in bundle.claims],
                contradictions=[c.model_dump() for c in bundle.contradictions],
                finding_ids=live_finding_ids,
            )
            if persist_cache is not None:
                persist_cache()

    return stats


def _bundle_from(structured: SectionBody, notes: list[dict]) -> EvidenceBundle:
    """Resolve note indices into concrete :class:`SourceRef` lists."""
    note_refs = _refs_per_note(notes)

    def resolve(indices: list[int]) -> list[SourceRef]:
        refs: list[SourceRef] = []
        for idx in indices:
            real = idx - 1
            if 0 <= real < len(note_refs):
                refs.extend(note_refs[real])
        return coalesce_refs(refs)

    claims = [Claim(text=c.text, sources=resolve(c.source_indices)) for c in structured.claims]
    contradictions = [
        Contradiction(
            summary=c.summary,
            positions=[Claim(text=p.text, sources=resolve(p.source_indices)) for p in c.positions],
        )
        for c in structured.contradictions
    ]
    return EvidenceBundle(body=structured.body, claims=claims, contradictions=contradictions)


def _refs_per_note(notes: list[dict]) -> list[list[SourceRef]]:
    """Map each note to its source refs.

    Notes produced by the modern extractor carry a ``sources`` list;
    older notes (or hand-written ones) fall back to a single SourceRef
    derived from the ``file`` field.
    """
    out: list[list[SourceRef]] = []
    for note in notes:
        sources = note.get("sources")
        if isinstance(sources, list) and sources:
            try:
                out.append([SourceRef.model_validate(s) for s in sources])
                continue
            except Exception:  # malformed sources — fall back to file
                pass
        file = note.get("file")
        if file:
            out.append([SourceRef(file=str(file))])
        else:
            out.append([])
    return out


def _render_user_prompt(section: Section, notes: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"## Section: {section.title} (id: {section.id})")
    lines.append("")
    lines.append("### Brief")
    lines.append(section.description)
    lines.append("")
    lines.append(f"### Notes from {len(notes)} file(s) — referenced by 1-based index in `source_indices`")
    for idx, note in enumerate(notes, start=1):
        file_ref = note.get("file", "?")
        summary = note.get("summary", "")
        finding = note.get("finding", "")
        sources = note.get("sources") or []
        ranges = ", ".join(_format_source(s) for s in sources) if sources else file_ref
        role = f" (file role: {summary})" if summary else ""
        lines.append(f"[{idx}] {ranges}{role}: {finding}")
    lines.append("")
    lines.append(
        "Synthesize a coherent markdown body for this section in `body`, "
        "and populate `claims` (with the 1-based note indices that justify "
        "each one) and `contradictions` for any disagreements. Follow the "
        "rules in the system prompt."
    )
    return "\n".join(lines)


def _format_source(source: dict | SourceRef) -> str:
    if isinstance(source, SourceRef):
        return source.render()
    file = source.get("file", "?")
    lines = source.get("lines")
    if not lines:
        return file
    if isinstance(lines, list | tuple) and len(lines) == 2:
        start, end = lines
        return f"{file}:{start}-{end}" if start != end else f"{file}:{start}"
    return file


def _empty_body(section: Section) -> str:
    return (
        f"_No findings were extracted for **{section.title}** during the last walk._\n\n"
        f"> Brief: {section.description}\n"
    )


def _fallback_body(section: Section, notes: list[dict], *, error: str) -> str:
    lines = [
        f"_Aggregation failed for **{section.title}** ({error}). Raw notes preserved below._\n",
        f"> Brief: {section.description}\n",
        "",
        "## Raw findings",
        "",
    ]
    for note in notes:
        file_ref = note.get("file", "?")
        finding = note.get("finding", "")
        lines.append(f"- **{file_ref}** — {finding}")
    return "\n".join(lines)


def aggregation_fully_cached(layout: WikiLayout, cache: WalkCache) -> bool:
    """Return True only if every primary section is covered by a fresh cache entry.

    "Fresh" means: live notes hash matches the cached ``notes_hash``.
    Empty-note sections count as covered only when a cache entry already
    asserts that the prior walk also saw zero notes — otherwise a file
    deletion that drains a section's notes would let the orchestrator
    skip stage 3 while last walk's prose is still on disk.

    The orchestrator's short-circuit relies on this: a walk that crashed
    mid-stage-3 leaves some sections aggregated and others stale, and a
    weaker predicate (just "extraction was 100% cached") would let the
    next walk skip stages 3 & 4 with stale prose still on disk.
    """
    for section in PRIMARY_SECTIONS:
        notes = read_notes(layout, section)
        notes_hash = hash_section_notes(notes)
        entry = cache.aggregation.get(section.id)
        if entry is None:
            return False
        if entry.notes_hash != notes_hash:
            return False
    return True


__all__ = [
    "AGGREGATION_SYSTEM_PROMPT",
    "AggregatedClaim",
    "AggregatedContradiction",
    "AggregationStats",
    "SectionBody",
    "aggregate_all",
    "aggregation_fully_cached",
]
# json kept for downstream debugging needs
_ = json
