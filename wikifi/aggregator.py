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
from dataclasses import dataclass

from pydantic import BaseModel, Field

from wikifi.cache import WalkCache, hash_section_notes
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


def aggregate_all(
    *,
    layout: WikiLayout,
    provider: LLMProvider,
    cache: WalkCache | None = None,
) -> AggregationStats:
    """Aggregate every primary section from its accumulated notes.

    Derivative sections (personas, user stories, diagrams) are populated by
    `wikifi.deriver.derive_all` after this stage — they have no per-file
    notes to aggregate from.

    When ``cache`` is supplied and the section's note digest is unchanged
    from the prior walk, the cached body and evidence are reused without
    invoking the LLM.
    """
    stats = AggregationStats()
    for section in PRIMARY_SECTIONS:
        notes = read_notes(layout, section)
        if not notes:
            write_section(layout, section, _empty_body(section))
            stats.sections_empty += 1
            continue

        notes_hash = hash_section_notes(notes)
        if cache is not None:
            cached = cache.lookup_aggregation(section.id, notes_hash)
            if cached is not None:
                bundle = EvidenceBundle(
                    body=cached.body,
                    claims=[Claim.model_validate(c) for c in cached.claims],
                    contradictions=[Contradiction.model_validate(c) for c in cached.contradictions],
                )
                write_section(layout, section, render_section_body(bundle))
                stats.sections_cached += 1
                stats.sections_written += 1
                continue

        try:
            structured = provider.complete_json(
                system=AGGREGATION_SYSTEM_PROMPT,
                user=_render_user_prompt(section, notes),
                schema=SectionBody,
            )
            bundle = _bundle_from(structured, notes)
            rendered = render_section_body(bundle)
        except Exception as exc:
            log.warning("aggregation failed for %s: %s", section.id, exc)
            rendered = _fallback_body(section, notes, error=str(exc))
            bundle = None

        write_section(layout, section, rendered)
        stats.sections_written += 1

        if cache is not None and bundle is not None:
            cache.record_aggregation(
                section.id,
                notes_hash=notes_hash,
                body=bundle.body,
                claims=[c.model_dump() for c in bundle.claims],
                contradictions=[c.model_dump() for c in bundle.contradictions],
            )

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


__all__ = [
    "AGGREGATION_SYSTEM_PROMPT",
    "AggregatedClaim",
    "AggregatedContradiction",
    "AggregationStats",
    "SectionBody",
    "aggregate_all",
]
# json kept for downstream debugging needs
_ = json
