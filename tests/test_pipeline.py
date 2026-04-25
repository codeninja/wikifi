"""End-to-end pipeline test using FakeProvider — no network."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wikifi.aggregation import aggregate
from wikifi.derivation import derive
from wikifi.extraction import extract_all
from wikifi.introspection import introspect
from wikifi.pipeline import run_walk
from wikifi.providers.fake import FakeProvider
from wikifi.schemas import (
    DERIVATIVE_SECTIONS,
    PRIMARY_SECTIONS,
    IntrospectionAssessment,
)
from wikifi.workspace import provision_workspace


def _scripted_handler() -> Any:
    """Return a handler that produces section-aware fixtures."""

    def _handle(prompt: str, system: str | None, schema: dict[str, Any] | None) -> str:
        if schema is not None and "primary_languages" in prompt:
            return json.dumps(
                {
                    "primary_languages": ["python"],
                    "inferred_purpose": "A pipeline that synthesizes a wiki from a codebase.",
                    "classification_rationale": "Python manifests are present.",
                    "in_scope_globs": ["src/**/*.py"],
                    "out_of_scope_globs": ["**/__init__.py"],
                    "notable_manifests": ["README.md"],
                }
            )
        if schema is not None:
            # extraction
            if "billing.py" in prompt:
                return json.dumps(
                    {
                        "role_summary": "Captures the responsibility for billing operations within the system.",
                        "findings": [
                            {
                                "section": "capabilities",
                                "finding": "Charges customers when an order is placed and reverses charges as needed.",
                            },
                            {
                                "section": "domains",
                                "finding": "Lives in the billing bounded context of the financial domain.",
                            },
                            {
                                "section": "entities",
                                "finding": "Account identifiers and monetary amounts are the core entities involved.",
                            },
                        ],
                        "skip_reason": None,
                    }
                )
            if "README.md" in prompt:
                return json.dumps(
                    {
                        "role_summary": "Communicates the system's stated purpose to readers.",
                        "findings": [
                            {
                                "section": "intent",
                                "finding": "Frames the system as a demo billing service for showcasing the platform.",
                            },
                        ],
                        "skip_reason": None,
                    }
                )
            return json.dumps({"role_summary": "irrelevant", "findings": [], "skip_reason": "no signal"})

        # Free-form synthesis: fabricate the right shape per requested section.
        if "Section to synthesize: **intent**" in prompt:
            return "## Intent\n\nThe system explains its purpose to users.\n"
        if "Section to synthesize:" in prompt:
            return "## Section\n\nNarrative content goes here.\n\n### Documented Gaps\nSome gaps remain.\n"
        if "Derive 2-4 user personas" in prompt:
            return (
                "## Personas\n\n### 1. Onboarding Practitioner\n"
                "- Goals: rapid comprehension.\n- Needs: navigable docs.\n"
            )
        if "Derive Gherkin-style user stories" in prompt:
            return (
                "## Stories\n\n### Feature: Charging\n"
                "**User Story** As a customer, I want to be charged, so that orders complete.\n\n"
                "```gherkin\nGiven an order\nWhen submitted\nThen the customer is charged\n```\n"
            )
        if "Produce three technology-agnostic diagrams" in prompt:
            return (
                "## Diagrams\n\n### Domain Map\n```mermaid\ngraph TD\nA --> B\n```\n"
                "**Key Observations:**\n- A connects to B.\n"
            )
        return "## Default\n\nFallback content.\n"

    return _handle


@pytest.fixture
def scripted_provider() -> FakeProvider:
    return FakeProvider(default_handler=_scripted_handler())


def test_introspect_with_fake(sample_repo: Path, scripted_provider, settings_factory):
    settings = settings_factory()
    scan_report, summary, assessment = introspect(root=sample_repo, settings=settings, provider=scripted_provider)
    assert assessment.inferred_purpose
    assert summary.file_count == len(scan_report.in_scope)
    assert any(p.name == "billing.py" for p in scan_report.in_scope)


def test_extract_all_writes_notes(sample_repo: Path, scripted_provider, settings_factory):
    settings = settings_factory()
    workspace = provision_workspace(sample_repo, wiki_dir_name=".wikifi")
    scan_report, _summary, assessment = introspect(root=workspace.root, settings=settings, provider=scripted_provider)
    stats = extract_all(
        workspace=workspace,
        scan_report=scan_report,
        assessment=assessment,
        settings=settings,
        provider=scripted_provider,
    )
    note_files = list(workspace.notes_dir.glob("*.json"))
    assert stats.notes_written == len(note_files) > 0


def test_aggregate_renders_primary_sections(sample_repo: Path, scripted_provider, settings_factory):
    settings = settings_factory()
    workspace = provision_workspace(sample_repo, wiki_dir_name=".wikifi")
    scan_report, _summary, assessment = introspect(root=workspace.root, settings=settings, provider=scripted_provider)
    extract_all(
        workspace=workspace,
        scan_report=scan_report,
        assessment=assessment,
        settings=settings,
        provider=scripted_provider,
    )
    stats = aggregate(
        workspace=workspace,
        assessment=assessment,
        settings=settings,
        provider=scripted_provider,
    )
    # All primary section files should exist after aggregate (synth or gap stanza).
    for section in PRIMARY_SECTIONS:
        path = workspace.section_path(section)
        assert path.is_file()
        body = path.read_text(encoding="utf-8")
        assert body.lstrip().startswith("##"), section
        assert not body.lstrip().startswith("# "), section
    assert stats.successful_writes >= 1


def test_derive_writes_personas_stories_diagrams(sample_repo: Path, scripted_provider, settings_factory):
    settings = settings_factory()
    workspace = provision_workspace(sample_repo, wiki_dir_name=".wikifi")
    # Pre-populate primary sections so derivation has input.
    for section in PRIMARY_SECTIONS:
        workspace.section_path(section).write_text(f"## {section}\n\nContent\n", encoding="utf-8")
    stats = derive(workspace=workspace, settings=settings, provider=scripted_provider)
    for section in DERIVATIVE_SECTIONS:
        assert workspace.section_path(section).is_file()
    assert stats.successful_writes >= 1


def test_run_walk_full_pipeline(sample_repo: Path, scripted_provider, settings_factory):
    settings = settings_factory()
    summary = run_walk(sample_repo, settings=settings, provider=scripted_provider)
    workspace_dir = sample_repo / ".wikifi"
    for section in (*PRIMARY_SECTIONS, *DERIVATIVE_SECTIONS):
        path = workspace_dir / f"{section}.md"
        assert path.is_file()
        body = path.read_text(encoding="utf-8")
        assert body.lstrip().startswith("##"), f"{section} body must start at H2, got: {body[:40]!r}"
    assert summary.extraction_notes_written > 0
    assert summary.primary_sections_written >= 1
    assert (workspace_dir / "execution_summary.md").is_file()


def test_introspection_falls_back_on_provider_error(sample_repo: Path, settings_factory):
    """When the introspection LLM call fails, the pipeline still produces a summary."""

    def _raises(prompt: str, system: str | None, schema: dict[str, Any] | None) -> str:
        from wikifi.providers.base import ProviderError

        raise ProviderError("simulated failure")

    settings = settings_factory()
    provider = FakeProvider(default_handler=_raises)
    scan_report, summary, assessment = introspect(root=sample_repo, settings=settings, provider=provider)
    assert isinstance(assessment, IntrospectionAssessment)
    assert "simulated failure" in assessment.classification_rationale
