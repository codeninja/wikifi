"""Coverage + quality report tests."""

from __future__ import annotations

from pathlib import Path

from wikifi.cache import WalkCache, save
from wikifi.critic import Critique
from wikifi.report import build_report
from wikifi.wiki import WikiLayout, append_note, initialize, write_section


def _layout(tmp_path: Path) -> WikiLayout:
    layout = WikiLayout(root=tmp_path)
    initialize(layout, model="m", provider="ollama", ollama_host="http://h")
    return layout


def test_build_report_without_provider_returns_structural_view(tmp_path: Path):
    layout = _layout(tmp_path)
    cache = WalkCache()
    cache.record_extraction(
        "src/order.py",
        fingerprint="abc",
        findings=[{"section_id": "entities", "finding": "Order", "sources": []}],
        summary="domain",
        chunks_processed=1,
    )
    cache.record_extraction(
        "src/empty.py",
        fingerprint="def",
        findings=[],
        summary="",
        chunks_processed=1,
    )
    save(layout, cache)
    append_note(layout, "entities", {"file": "src/order.py", "summary": "x", "finding": "Order"})
    write_section(layout, "entities", "Body for entities.")

    report = build_report(layout=layout, provider=None, score=False)

    assert report.coverage.files_total == 2
    assert report.coverage.files_with_findings == 1
    assert report.coverage.coverage_pct() == 50.0
    assert report.overall_score is None
    md = report.render()
    assert "wikifi coverage" in md
    assert "`entities`" in md


def test_build_report_with_score_uses_provider(tmp_path: Path, mock_provider_factory):
    layout = _layout(tmp_path)
    write_section(layout, "entities", "An entity body.")
    write_section(layout, "intent", "Intent body.")

    provider = mock_provider_factory(
        json_factory=lambda schema, system, user: Critique(score=9, summary="great"),
    )
    report = build_report(layout=layout, provider=provider, score=True)

    populated = [s for s in report.sections if s.critique is not None]
    assert populated, "expected at least one populated section to be scored"
    assert all(s.critique.score == 9 for s in populated)
    assert report.overall_score == 9.0
    assert "9/10" in report.render()


def test_build_report_marks_unpopulated_sections(tmp_path: Path):
    """Sections still bearing the init placeholder are flagged ``is_empty``."""
    layout = _layout(tmp_path)
    save(layout, WalkCache())
    report = build_report(layout=layout, provider=None, score=False)
    assert any(entry.is_empty for entry in report.sections)
