"""Section-quality critic.

Two consumers:

- :func:`review_section` runs a *critic + reviser* loop on a synthesized
  section body. The critic scores the body against its brief and the
  upstream evidence, identifying unsupported claims and gaps. If the
  score falls below ``min_score`` the reviser is invoked once with the
  critique to produce an improved body. This catches the bulk of
  hallucination and missing-coverage failures on derivative sections,
  where a single-shot synthesis is most error-prone.
- :func:`score_wiki` walks every section in the wiki and produces a
  rubric-style report (used by ``wikifi report``).

The two paths share a single Pydantic schema (:class:`Critique`) so the
provider implementation can cache the system prompt across both.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from wikifi.providers.base import LLMProvider
from wikifi.sections import Section

log = logging.getLogger("wikifi.critic")


CRITIC_SYSTEM_PROMPT = """\
You are wikifi's quality critic. You receive (a) the brief for a section of \
a technology-agnostic wiki, (b) the synthesized markdown body, and \
optionally (c) the upstream evidence the body was supposed to derive from. \
You score the body on a 0–10 rubric and identify concrete improvements.

Rubric:
- 9–10: tech-agnostic, fully grounded in evidence, narratively coherent, \
  no unsupported claims, no obvious gaps against the brief.
- 6–8: largely sound but with one or more issues — minor unsupported \
  claims, awkward narrative, or missed coverage of brief items.
- 3–5: substantial gaps, several unsupported claims, or partial coverage.
- 0–2: incoherent, dominated by speculation, or off-brief.

Be specific in `unsupported_claims` and `gaps`. A migration team will use \
your critique to decide whether the section is ready to ship.
"""


REVISER_SYSTEM_PROMPT = """\
You are wikifi's section reviser. You receive (a) the section brief, \
(b) the prior body, (c) a critique flagging unsupported claims and gaps, \
and (d) the upstream evidence available. Produce a revised body that \
addresses every flagged issue. Stay tech-agnostic. Do not invent claims \
the upstreams cannot support — declare gaps explicitly when evidence is \
missing. Output the body only, no top-level heading.
"""


class Critique(BaseModel):
    """Structured critic output."""

    score: int = Field(ge=0, le=10, description="Overall quality score (0–10).")
    summary: str = Field(default="", description="One- or two-sentence overall judgment.")
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Statements in the body not supported by the upstream evidence.",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Brief items the body fails to cover.",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Concrete edits the reviser should make.",
    )


class RevisedBody(BaseModel):
    body: str = Field(description="Revised markdown body for the section.")


@dataclass
class ReviewOutcome:
    section_id: str
    initial: Critique
    body: str
    revised: bool = False
    final: Critique | None = None


@dataclass
class WikiQualityReport:
    overall_score: float
    critiques: dict[str, Critique] = field(default_factory=dict)
    coverage: CoverageStats | None = None


def review_section(
    *,
    section: Section,
    body: str,
    upstream_evidence: Mapping[str, str] | None,
    provider: LLMProvider,
    min_score: int = 7,
) -> ReviewOutcome:
    """Critique → optionally revise → critique again. Returns the outcome."""
    initial = _critique(section=section, body=body, upstream=upstream_evidence, provider=provider)
    outcome = ReviewOutcome(section_id=section.id, initial=initial, body=body)
    if initial.score >= min_score or not (initial.unsupported_claims or initial.gaps):
        return outcome

    try:
        revised = provider.complete_json(
            system=REVISER_SYSTEM_PROMPT,
            user=_render_revise_prompt(section, body, initial, upstream_evidence),
            schema=RevisedBody,
        )
    except Exception as exc:
        log.warning("reviser failed for %s: %s", section.id, exc)
        return outcome

    follow_up = _critique(section=section, body=revised.body, upstream=upstream_evidence, provider=provider)
    # Only accept the revision if it actually improved the score; otherwise
    # keep the original to avoid regressions caused by a confused reviser.
    if follow_up.score >= initial.score:
        outcome.body = revised.body
        outcome.revised = True
        outcome.final = follow_up
    else:
        log.info(
            "discarding revision for %s — score dropped from %d to %d",
            section.id,
            initial.score,
            follow_up.score,
        )
    return outcome


def _critique(
    *,
    section: Section,
    body: str,
    upstream: Mapping[str, str] | None,
    provider: LLMProvider,
) -> Critique:
    user = _render_critique_prompt(section, body, upstream)
    try:
        return provider.complete_json(system=CRITIC_SYSTEM_PROMPT, user=user, schema=Critique)
    except Exception as exc:
        log.warning("critic failed for %s: %s", section.id, exc)
        return Critique(score=0, summary=f"Critic unavailable ({exc}).")


def _render_critique_prompt(
    section: Section,
    body: str,
    upstream: Mapping[str, str] | None,
) -> str:
    parts = [
        f"## Section: {section.title} (id: {section.id})",
        "",
        "### Brief",
        section.description,
        "",
        "### Body to evaluate",
        "```markdown",
        body.strip() or "(empty body)",
        "```",
    ]
    if upstream:
        parts += ["", "### Upstream evidence available"]
        for upstream_id, content in upstream.items():
            parts.append(f"#### {upstream_id}")
            parts.append("```markdown")
            parts.append(content.strip())
            parts.append("```")
    parts.append("")
    parts.append("Score the body and list unsupported claims, gaps, and suggested edits.")
    return "\n".join(parts)


def _render_revise_prompt(
    section: Section,
    body: str,
    critique: Critique,
    upstream: Mapping[str, str] | None,
) -> str:
    parts = [
        f"## Section: {section.title} (id: {section.id})",
        "",
        "### Brief",
        section.description,
        "",
        "### Prior body",
        "```markdown",
        body.strip() or "(empty)",
        "```",
        "",
        "### Critique",
        f"score: {critique.score}/10",
    ]
    if critique.unsupported_claims:
        parts.append("Unsupported claims to remove or qualify:")
        parts += [f"- {c}" for c in critique.unsupported_claims]
    if critique.gaps:
        parts.append("Gaps to fill (only when evidence allows):")
        parts += [f"- {g}" for g in critique.gaps]
    if critique.suggestions:
        parts.append("Suggested edits:")
        parts += [f"- {s}" for s in critique.suggestions]
    if upstream:
        parts += ["", "### Upstream evidence"]
        for upstream_id, content in upstream.items():
            parts.append(f"#### {upstream_id}")
            parts.append("```markdown")
            parts.append(content.strip())
            parts.append("```")
    parts.append("")
    parts.append("Output the revised body only.")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Coverage stats — populated by the extractor + aggregator caches and
# rendered by `wikifi report`.
# ---------------------------------------------------------------------------


@dataclass
class CoverageStats:
    files_total: int
    files_with_findings: int
    findings_per_section: dict[str, int]
    files_per_section: dict[str, int]

    def coverage_pct(self) -> float:
        if self.files_total == 0:
            return 0.0
        return round(100.0 * self.files_with_findings / self.files_total, 1)
