"""Critic + reviser tests."""

from __future__ import annotations

from wikifi.aggregator import SectionBody  # for unused import sanity
from wikifi.critic import (
    CoverageStats,
    Critique,
    RevisedBody,
    review_section,
)
from wikifi.sections import SECTIONS_BY_ID

_ = SectionBody  # silence "imported but unused"


def test_review_skips_revision_when_score_meets_threshold(mock_provider_factory):
    section = SECTIONS_BY_ID["entities"]
    provider = mock_provider_factory(
        json_responses={
            Critique: [Critique(score=8, summary="solid")],
        }
    )
    outcome = review_section(
        section=section,
        body="Bodies of evidence here.",
        upstream_evidence=None,
        provider=provider,
        min_score=7,
    )
    assert outcome.revised is False
    assert outcome.body == "Bodies of evidence here."


def test_review_revises_when_score_below_threshold(mock_provider_factory):
    section = SECTIONS_BY_ID["entities"]
    queue_critique = [
        Critique(score=4, summary="weak", unsupported_claims=["X"], gaps=["Y"]),
        Critique(score=8, summary="better"),
    ]

    def factory(schema, system, user):
        if schema is Critique:
            return queue_critique.pop(0)
        if schema is RevisedBody:
            return RevisedBody(body="Revised body that addresses X and Y.")
        raise AssertionError(f"unexpected schema {schema}")

    provider = mock_provider_factory(json_factory=factory)

    outcome = review_section(
        section=section,
        body="Original body.",
        upstream_evidence={"intent": "upstream content"},
        provider=provider,
        min_score=7,
    )
    assert outcome.revised is True
    assert "Revised body" in outcome.body
    assert outcome.final is not None
    assert outcome.final.score == 8


def test_review_keeps_original_when_revision_regresses(mock_provider_factory):
    section = SECTIONS_BY_ID["entities"]
    critiques = [
        Critique(score=5, gaps=["Y"]),
        Critique(score=3),  # revision is worse
    ]

    def factory(schema, system, user):
        if schema is Critique:
            return critiques.pop(0)
        if schema is RevisedBody:
            return RevisedBody(body="Worse body.")
        raise AssertionError

    provider = mock_provider_factory(json_factory=factory)

    outcome = review_section(
        section=section,
        body="Original body.",
        upstream_evidence=None,
        provider=provider,
        min_score=7,
    )
    assert outcome.revised is False
    assert outcome.body == "Original body."


def test_review_handles_critic_failure(mock_provider_factory):
    """If the critic call fails, score=0 → no revision attempt; the body stays."""
    section = SECTIONS_BY_ID["entities"]

    def factory(schema, system, user):
        raise RuntimeError("model unavailable")

    provider = mock_provider_factory(json_factory=factory)
    outcome = review_section(
        section=section,
        body="Body.",
        upstream_evidence=None,
        provider=provider,
        min_score=7,
    )
    assert outcome.body == "Body."
    assert outcome.initial.score == 0


def test_coverage_stats_pct():
    stats = CoverageStats(
        files_total=100,
        files_with_findings=42,
        findings_per_section={},
        files_per_section={},
    )
    assert stats.coverage_pct() == 42.0
    assert CoverageStats(0, 0, {}, {}).coverage_pct() == 0.0
