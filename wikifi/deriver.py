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
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from wikifi.cache import WalkCache, hash_upstream_bodies
from wikifi.critic import ReviewOutcome, review_section
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
    sections_revised: int = 0
    sections_cached: int = 0
    review_outcomes: list[ReviewOutcome] = field(default_factory=list)


def derive_all(
    *,
    layout: WikiLayout,
    provider: LLMProvider,
    review: bool = False,
    review_min_score: int = 7,
    cache: WalkCache | None = None,
    persist_cache: Callable[[], None] | None = None,
) -> DerivationStats:
    """Synthesize every derivative section from its upstream primary sections.

    With ``review=True`` each derivative is run through the critic +
    reviser loop after synthesis. The critic loop is the highest-leverage
    quality lever for derivative sections — personas and Gherkin stories
    are exactly where single-shot synthesis tends to hallucinate.

    When ``cache`` is supplied and the upstream bodies are unchanged from
    the prior walk (and ``review`` parity holds — see
    :meth:`WalkCache.lookup_derivation`), the cached body is replayed
    rather than re-synthesized. Combined with the aggregator's cache,
    this is what makes a no-change re-walk a no-op LLM-wise.
    """
    stats = DerivationStats()
    for section in DERIVATIVE_SECTIONS:
        upstream_bodies = _collect_upstream(layout, section)
        if not upstream_bodies:
            log.warning(
                "deriver: %s has no upstream content (upstreams=%s); skipping",
                section.id,
                section.derived_from,
            )
            empty_body = _empty_body(section)
            write_section(layout, section, empty_body)
            stats.sections_skipped += 1
            # Record an empty-state cache entry so the orchestrator's
            # full-cache short-circuit can tell "we wrote the empty
            # placeholder last walk too" apart from "we never ran stage
            # 4 for this section, body on disk is stale." Mirrors the
            # empty-notes path in the aggregator.
            #
            # ``revised=review`` is set to the requested mode (not
            # whether a critic ran — none did, the empty path skipped
            # the loop). Storing it this way keeps the next
            # ``--review`` walk's freshness check from rejecting this
            # entry as "unreviewed"; the empty placeholder body has no
            # claims for a critic to evaluate either way.
            if cache is not None:
                cache.record_derivation(
                    section.id,
                    upstream_hash=hash_upstream_bodies({}),
                    body=empty_body,
                    revised=review,
                )
                if persist_cache is not None:
                    persist_cache()
            continue

        upstream_hash = hash_upstream_bodies(upstream_bodies)
        if cache is not None:
            cached = cache.lookup_derivation(section.id, upstream_hash, expect_revised=review)
            if cached is not None:
                write_section(layout, section, cached.body)
                stats.sections_cached += 1
                stats.sections_derived += 1
                # ``sections_revised`` counts reviser work performed in
                # this walk. Replay from cache means no critic ran, so
                # the counter stays put even if the cached body went
                # through review on a prior walk.
                continue

        derivation_failed = False
        try:
            body = provider.complete_json(
                system=DERIVATION_SYSTEM_PROMPT,
                user=_render_user_prompt(section, upstream_bodies),
                schema=DerivedSection,
            ).body
        except Exception as exc:
            log.warning("derivation failed for %s: %s", section.id, exc)
            body = _fallback_body(section, upstream_bodies, error=str(exc))
            derivation_failed = True

        # ``revised`` records whether the critic + reviser loop ran on
        # this body, not whether the reviser changed any text. A walk
        # invoked with ``--review`` whose critic accepts the draft
        # unchanged has still passed review; treating it as "unrevised"
        # would force the next ``--review`` walk to redo the loop.
        reviewed = False
        if review:
            outcome = review_section(
                section=section,
                body=body,
                upstream_evidence=upstream_bodies,
                provider=provider,
                min_score=review_min_score,
            )
            body = outcome.body
            stats.review_outcomes.append(outcome)
            reviewed = True
            if outcome.revised:
                stats.sections_revised += 1

        write_section(layout, section, body)
        stats.sections_derived += 1

        # Don't cache an error body — caching it would let later walks
        # replay or short-circuit around a transient stage-4 outage
        # until the upstream bodies change.
        if cache is not None and not derivation_failed:
            cache.record_derivation(
                section.id,
                upstream_hash=upstream_hash,
                body=body,
                revised=reviewed,
            )
            if persist_cache is not None:
                persist_cache()
    return stats


def derivation_fully_cached(layout: WikiLayout, cache: WalkCache, *, review: bool) -> bool:
    """Return True only if every derivative section is covered by a fresh cache entry.

    Mirrors :func:`wikifi.aggregator.aggregation_fully_cached`. A section
    counts as covered when its cache entry's ``upstream_hash`` matches
    the hash of the upstream bodies currently on disk *and* the
    ``revised`` flag matches the requested review mode (so a
    ``--review`` re-walk doesn't silently inherit a non-reviewed body).

    Sections with no upstream content require a cache entry too — the
    empty-upstream path in :func:`derive_all` records one with the
    empty-payload hash so an aggregation that drains a derivative's
    upstreams forces re-derivation rather than freezing stale prose.
    """
    for section in DERIVATIVE_SECTIONS:
        upstream_bodies = _collect_upstream(layout, section)
        upstream_hash = hash_upstream_bodies(upstream_bodies)
        entry = cache.derivation.get(section.id)
        if entry is None:
            return False
        if entry.upstream_hash != upstream_hash:
            return False
        if review and not entry.revised:
            return False
    return True


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
