"""``wikifi report`` — coverage and quality view of the wiki.

The report answers two questions migration leads ask before they fund a
re-implementation:

1. **Did the walk cover the system?** Per-section file/finding counts,
   total files seen vs. files that contributed something.
2. **Is the wiki good enough to act on?** Per-section quality score from
   the critic, with the headline ``unsupported_claims`` and ``gaps``.

The report runs purely from on-disk artifacts (notes JSONL + section
markdown + cache) plus optional provider-driven scoring; it never
modifies the wiki.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from wikifi.cache import WalkCache, load
from wikifi.critic import CoverageStats, Critique, _critique
from wikifi.providers.base import LLMProvider
from wikifi.sections import PRIMARY_SECTIONS, SECTIONS, Section
from wikifi.wiki import WikiLayout, read_notes

log = logging.getLogger("wikifi.report")


@dataclass
class SectionReport:
    section: Section
    files_contributing: int
    findings_count: int
    body_chars: int
    is_empty: bool
    critique: Critique | None = None


@dataclass
class WikiReport:
    coverage: CoverageStats
    sections: list[SectionReport] = field(default_factory=list)
    overall_score: float | None = None

    def render(self) -> str:
        lines: list[str] = []
        lines.append("# wikifi coverage + quality report")
        lines.append("")
        lines.append(
            f"Files seen: **{self.coverage.files_total}**  ·  "
            f"Files with findings: **{self.coverage.files_with_findings}** "
            f"({self.coverage.coverage_pct()}%)"
        )
        if self.overall_score is not None:
            lines.append(f"Overall section score (mean of populated sections): **{self.overall_score:.1f} / 10**")
        lines.append("")
        lines.append("| Section | Files | Findings | Body | Score | Headline gap |")
        lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
        for entry in self.sections:
            score = "—" if entry.critique is None else f"{entry.critique.score}/10"
            gap = ""
            if entry.critique and entry.critique.gaps:
                gap = entry.critique.gaps[0][:60]
            elif entry.critique and entry.critique.unsupported_claims:
                gap = "unsupported: " + entry.critique.unsupported_claims[0][:50]
            elif entry.is_empty:
                gap = "no findings"
            lines.append(
                f"| `{entry.section.id}` "
                f"| {entry.files_contributing} "
                f"| {entry.findings_count} "
                f"| {entry.body_chars} "
                f"| {score} "
                f"| {gap} |"
            )
        return "\n".join(lines)


def build_report(
    *,
    layout: WikiLayout,
    provider: LLMProvider | None = None,
    score: bool = False,
) -> WikiReport:
    """Inspect a wiki and produce a :class:`WikiReport`.

    With ``score=True`` and a provider supplied, every populated section
    is run through the critic for a quality score. Without that, the
    report is purely structural — useful in CI without an LLM.
    """
    files_total, files_with_findings = _coverage_from_cache(layout)
    findings_per_section: dict[str, int] = {}
    files_per_section: dict[str, int] = {}
    for section in PRIMARY_SECTIONS:
        notes = read_notes(layout, section)
        findings_per_section[section.id] = len(notes)
        files_per_section[section.id] = len({n.get("file") for n in notes if n.get("file")})

    coverage = CoverageStats(
        files_total=files_total,
        files_with_findings=files_with_findings,
        findings_per_section=findings_per_section,
        files_per_section=files_per_section,
    )

    section_reports: list[SectionReport] = []
    scored: list[int] = []
    for section in SECTIONS:
        path = layout.section_path(section)
        body = path.read_text(encoding="utf-8") if path.exists() else ""
        is_empty = (
            "Not yet populated" in body
            or "No findings were extracted" in body
            or "upstream sections required to derive" in body.lower()
        )
        critique: Critique | None = None
        if score and provider is not None and not is_empty and body.strip():
            critique = _critique(
                section=section,
                body=body,
                upstream=_collect_upstream(layout, section) if section.tier == "derivative" else None,
                provider=provider,
            )
            scored.append(critique.score)
        section_reports.append(
            SectionReport(
                section=section,
                files_contributing=files_per_section.get(section.id, 0),
                findings_count=findings_per_section.get(section.id, 0),
                body_chars=len(body),
                is_empty=is_empty,
                critique=critique,
            )
        )

    overall = sum(scored) / len(scored) if scored else None
    return WikiReport(coverage=coverage, sections=section_reports, overall_score=overall)


def _coverage_from_cache(layout: WikiLayout) -> tuple[int, int]:
    cache: WalkCache = load(layout)
    files_total = len(cache.extraction)
    files_with_findings = sum(1 for entry in cache.extraction.values() if entry.findings)
    return files_total, files_with_findings


def _collect_upstream(layout: WikiLayout, section: Section) -> dict[str, str]:
    bodies: dict[str, str] = {}
    for upstream_id in section.derived_from:
        path = layout.section_path(upstream_id)
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if "Not yet populated" not in text and "No findings were extracted" not in text:
                bodies[upstream_id] = text
    return bodies
