"""Stage 4 — derivative section synthesis.

Some sections cannot be extracted from individual files because they emerge
from the *aggregate* of what the system does:

- **Personas** are inferred from capabilities, intent, entities, and
  integrations — no single file declares "I serve persona X."
- **User stories** weave personas, capabilities, and entities into Gherkin —
  they are a derivative cascade.
- **Diagrams** render relationships across domains, entities, and
  integrations rather than reading from any one file.

This module runs after the aggregator. For each derivative section it loads
the upstream sections' final markdown bodies, hands them to the model with
the derivative section's brief, and writes the resulting markdown.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from wikifi.providers.base import LLMProvider
from wikifi.sections import DERIVATIVE_SECTIONS, SECTIONS_BY_ID, Section
from wikifi.wiki import WikiLayout, write_section

log = logging.getLogger("wikifi.deriver")


DERIVATION_SYSTEM_PROMPT = """\
You are wikifi's derivative-section synthesizer. You receive the final \
markdown of one or more upstream sections of a technology-agnostic wiki, \
plus a brief for one derivative section. Produce a coherent markdown body \
for the derivative section, grounded entirely in the upstream content.

Rules:
- Only the upstream sections are evidence. Do not invent facts that are not \
  supported by them. If the upstreams are silent on something, declare the \
  gap rather than fill it.
- Stay tech-agnostic. Never name languages, frameworks, or libraries — \
  translate every observation into domain terms.
- Use markdown sub-headings, lists, and tables where they help the reader.
- For Gherkin-style outputs, use proper `Given/When/Then` blocks inside \
  fenced ```gherkin code blocks.
- For diagrams, emit valid Mermaid inside fenced ```mermaid code blocks. \
  Prefer `graph`, `classDiagram`, `erDiagram`, and `sequenceDiagram`.
- Output the body only. Do not repeat the section title (the writer adds it).
"""


class DerivedSection(BaseModel):
    """The final markdown body for a derivative section."""

    body: str = Field(description="Markdown content for the section, no top-level heading.")


@dataclass
class DerivationStats:
    sections_derived: int = 0
    sections_skipped: int = 0


def derive_all(*, layout: WikiLayout, provider: LLMProvider) -> DerivationStats:
    """Synthesize every derivative section from its upstream primary sections."""
    stats = DerivationStats()
    for section in DERIVATIVE_SECTIONS:
        upstream_bodies = _collect_upstream(layout, section)
        if not upstream_bodies:
            log.warning(
                "deriver: %s has no upstream content (upstreams=%s); skipping",
                section.id,
                section.derived_from,
            )
            write_section(layout, section, _empty_body(section))
            stats.sections_skipped += 1
            continue
        try:
            body = provider.complete_json(
                system=DERIVATION_SYSTEM_PROMPT,
                user=_render_user_prompt(section, upstream_bodies),
                schema=DerivedSection,
            ).body
        except Exception as exc:
            log.warning("derivation failed for %s: %s", section.id, exc)
            body = _fallback_body(section, upstream_bodies, error=str(exc))
        write_section(layout, section, body)
        stats.sections_derived += 1
    return stats


def _collect_upstream(layout: WikiLayout, section: Section) -> dict[str, str]:
    """Read the final markdown bodies of every upstream section for `section`.

    Sections that haven't been written yet, or that contain only the empty
    placeholder, are skipped — there's nothing to derive from.
    """
    bodies: dict[str, str] = {}
    for upstream_id in section.derived_from:
        if upstream_id not in SECTIONS_BY_ID:
            continue
        path = layout.section_path(upstream_id)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if _looks_empty(text):
            continue
        bodies[upstream_id] = text
    return bodies


def _looks_empty(text: str) -> bool:
    """Heuristic for placeholder bodies (init, aggregator-empty, deriver-empty).

    Each upstream check must catch every shape of "this section has no real
    content", or a derivative will see a placeholder as evidence and fabricate
    findings from a literal "Not yet populated" message.
    """
    lowered = text.lower()
    return (
        "not yet populated" in lowered  # `wikifi.wiki._empty_section`
        or "no findings were extracted" in lowered  # `wikifi.aggregator._empty_body`
        or "upstream sections required to derive" in lowered  # this module's `_empty_body`
    )


def _render_user_prompt(section: Section, upstream_bodies: dict[str, str]) -> str:
    lines: list[str] = []
    lines.append(f"## Derivative section: {section.title} (id: {section.id})")
    lines.append("")
    lines.append("### Brief")
    lines.append(section.description)
    lines.append("")
    lines.append("### Upstream sections (the only evidence available)")
    for upstream_id, body in upstream_bodies.items():
        upstream = SECTIONS_BY_ID[upstream_id]
        lines.append(f"#### Upstream: {upstream.title} (id: {upstream_id})")
        lines.append("```markdown")
        lines.append(body.strip())
        lines.append("```")
        lines.append("")
    lines.append("Produce the derivative section's markdown body, grounded only in the upstreams above.")
    return "\n".join(lines)


def _empty_body(section: Section) -> str:
    return (
        f"_The upstream sections required to derive **{section.title}** were not populated "
        f"during the last walk._\n\n"
        f"> Brief: {section.description}\n\n"
        f"> Upstream sections: {', '.join(section.derived_from)}\n"
    )


def _fallback_body(section: Section, upstream_bodies: dict[str, str], *, error: str) -> str:
    lines = [
        f"_Derivation failed for **{section.title}** ({error}). Upstream evidence preserved below._\n",
        f"> Brief: {section.description}\n",
        "",
    ]
    for upstream_id, body in upstream_bodies.items():
        lines.append(f"## From {upstream_id}")
        lines.append(body.strip())
        lines.append("")
    return "\n".join(lines)
