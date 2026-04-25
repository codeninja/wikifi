"""Stage 3 — per-section synthesis.

Reads the JSONL notes accumulated by the extractor and asks the LLM to
synthesize each section's final markdown. One LLM call per section, with the
section description as the contract for what should appear and what shouldn't.

Sections with zero notes get a placeholder body so the wiki layout stays
complete and the absence is visible.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from wikifi.providers.base import LLMProvider
from wikifi.sections import SECTIONS, Section
from wikifi.wiki import WikiLayout, read_notes, write_section

log = logging.getLogger("wikifi.aggregator")

AGGREGATION_SYSTEM_PROMPT = """\
You are wikifi's section aggregator. You receive structured notes that an \
extractor pass collected from individual source files in a target codebase, \
along with the brief for one section of a tech-agnostic wiki. Synthesize a \
clean markdown body for that section.

Rules:
- Tech-agnostic. Never mention specific languages, frameworks, or libraries. \
  Translate every observation into domain terms.
- Coherent narrative — not a transcript of the notes. Merge duplicates, \
  resolve contradictions, organize by domain logic.
- Use markdown sub-headings, lists, and tables where they help the reader.
- If notes are sparse or contradictory, say so plainly. Better to declare a \
  gap than to invent content.
- Output the body only. Do not repeat the section title (the writer adds it).
"""


class SectionBody(BaseModel):
    """The final markdown body for a section."""

    body: str = Field(description="Markdown content for the section, no top-level heading.")


@dataclass
class AggregationStats:
    sections_written: int = 0
    sections_empty: int = 0


def aggregate_all(*, layout: WikiLayout, provider: LLMProvider) -> AggregationStats:
    """Aggregate every section in the taxonomy and write its markdown file."""
    stats = AggregationStats()
    for section in SECTIONS:
        notes = read_notes(layout, section)
        if not notes:
            write_section(layout, section, _empty_body(section))
            stats.sections_empty += 1
            continue
        try:
            body = provider.complete_json(
                system=AGGREGATION_SYSTEM_PROMPT,
                user=_render_user_prompt(section, notes),
                schema=SectionBody,
            ).body
        except Exception as exc:
            log.warning("aggregation failed for %s: %s", section.id, exc)
            body = _fallback_body(section, notes, error=str(exc))
        write_section(layout, section, body)
        stats.sections_written += 1
    return stats


def _render_user_prompt(section: Section, notes: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"## Section: {section.title} (id: {section.id})")
    lines.append("")
    lines.append("### Brief")
    lines.append(section.description)
    lines.append("")
    lines.append(f"### Notes from {len(notes)} file(s)")
    for note in notes:
        file_ref = note.get("file", "?")
        summary = note.get("summary", "")
        finding = note.get("finding", "")
        lines.append(f"- [{file_ref}] (file role: {summary}) {finding}")
    lines.append("")
    lines.append(
        "Synthesize a coherent markdown body for this section. Follow the rules in the system prompt."
    )
    return "\n".join(lines)


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
