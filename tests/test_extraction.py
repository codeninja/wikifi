from __future__ import annotations

from pathlib import Path

from wikifi.extraction import extract_notes
from wikifi.models import IntrospectionAssessment, SourceFile
from wikifi.providers import LLMProvider, ProviderError


class BrokenProvider(LLMProvider):
    provider_id = "ollama"

    def generate_text(self, *, system: str, prompt: str) -> str:
        raise ProviderError("offline")

    def generate_json(self, *, system: str, prompt: str, schema: dict) -> dict:
        raise ProviderError("offline")


class StructuredProvider(LLMProvider):
    provider_id = "ollama"

    def generate_text(self, *, system: str, prompt: str) -> str:
        return "not used"

    def generate_json(self, *, system: str, prompt: str, schema: dict) -> dict:
        return {
            "role_summary": "Coordinates repository analysis for operators.",
            "finding": "The artifact turns source evidence into documentation intent.",
            "categories": {
                "capabilities": ["Produces a source-backed wiki."],
                "integrations": "Hands work from command input to processing stages.",
                "unknown": ["ignored"],
            },
            "gaps": ["Provider cannot infer authorization rules."],
        }


def test_extraction_accepts_structured_provider_output(tmp_path) -> None:
    path = tmp_path / "workflow.py"
    content = "def run_pipeline():\n    return 'stage handoff status summary'\n"
    path.write_text(content, encoding="utf-8")
    source = SourceFile(
        path=path,
        relative_path="workflow.py",
        size_bytes=len(content),
        content=content,
        truncated=False,
        digest="abc",
    )
    assessment = IntrospectionAssessment(
        primary_languages=("Application source",),
        inferred_purpose="A workflow documentation system.",
        classification_rationale="Structural data only.",
        scope_description="One selected file.",
    )

    notes, status = extract_notes((source,), assessment, StructuredProvider(), allow_fallback=True)

    assert status == "provider ollama completed extraction"
    assert notes[0].role_summary == "Coordinates repository analysis for operators."
    assert notes[0].categories["capabilities"] == ["Produces a source-backed wiki."]
    assert notes[0].categories["integrations"] == ["Hands work from command input to processing stages."]
    assert notes[0].gaps == ("Provider cannot infer authorization rules.",)


def test_extraction_uses_deterministic_fallback_when_provider_fails(tmp_path) -> None:
    path = tmp_path / "workflow.py"
    content = "class Workflow:\n    def run_pipeline(self):\n        return 'stage handoff status summary'\n"
    path.write_text(content, encoding="utf-8")
    source = SourceFile(
        path=path,
        relative_path="workflow.py",
        size_bytes=len(content),
        content=content,
        truncated=False,
        digest="abc",
    )
    assessment = IntrospectionAssessment(
        primary_languages=("Application source",),
        inferred_purpose="A workflow documentation system.",
        classification_rationale="Structural data only.",
        scope_description="One selected file.",
    )

    notes, status = extract_notes((source,), assessment, BrokenProvider(), allow_fallback=True)

    assert "deterministic fallback used for 1 file" in status
    assert len(notes) == 1
    assert notes[0].file_reference == "workflow.py"
    assert notes[0].categories["capabilities"]
    assert notes[0].categories["integrations"]
    assert notes[0].gaps


def test_extraction_can_be_configured_to_fail_without_fallback(tmp_path) -> None:
    path = Path(tmp_path / "workflow.py")
    source = SourceFile(
        path=path,
        relative_path="workflow.py",
        size_bytes=80,
        content="def run_pipeline():\n    return 'stage handoff status summary'\n",
        truncated=False,
        digest="abc",
    )
    assessment = IntrospectionAssessment(
        primary_languages=("Application source",),
        inferred_purpose="A workflow documentation system.",
        classification_rationale="Structural data only.",
        scope_description="One selected file.",
    )

    try:
        extract_notes((source,), assessment, BrokenProvider(), allow_fallback=False)
    except ProviderError as exc:
        assert "offline" in str(exc)
    else:
        raise AssertionError("ProviderError was not raised")
