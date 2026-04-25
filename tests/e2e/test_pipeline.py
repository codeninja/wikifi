from __future__ import annotations

import json

from wikifi.orchestrator import walk
from wikifi.providers import LLMProvider, ProviderError


class OfflineOllamaProvider(LLMProvider):
    provider_id = "ollama"

    def generate_text(self, *, system: str, prompt: str) -> str:
        raise ProviderError("offline test provider")

    def generate_json(self, *, system: str, prompt: str, schema: dict) -> dict:
        raise ProviderError("offline test provider")


def test_pipeline_writes_complete_workspace_with_provider_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("wikifi.orchestrator.build_provider", lambda settings: OfflineOllamaProvider())
    (tmp_path / "README.md").write_text("# Claims Platform\n\nCoordinates claim intake and review.", encoding="utf-8")
    (tmp_path / "claims.py").write_text(
        "\n".join(
            [
                "class Claim:",
                "    def submit(self):",
                "        return 'captures customer loss narrative and review status'",
                "",
                "class ReviewQueue:",
                "    def assign(self):",
                "        return 'routes cases to specialists with audit summary'",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "empty.py").write_text("# stub\n", encoding="utf-8")

    result = walk(tmp_path)

    assert result.completion_status == "completed"
    assert result.stage_metrics["stage_order"] == ["introspection", "extraction", "aggregation", "derivation"]
    assert result.provider_status == "provider degraded; deterministic fallback used for 1 file(s)"
    assert result.directory_summary.selected_file_count == 1
    assert len(result.notes) == 1
    assert result.aggregation_stats.successful_writes == 9
    assert result.derivative_stats.successful_writes == 3

    wiki_dir = tmp_path / ".wikifi"
    expected_sections = {
        "capabilities.md",
        "cross_cutting.md",
        "domains.md",
        "entities.md",
        "external_dependencies.md",
        "hard_specifications.md",
        "inline_schematics.md",
        "integrations.md",
        "intent.md",
    }
    assert {path.name for path in (wiki_dir / "sections").glob("*.md")} == expected_sections
    assert {path.name for path in (wiki_dir / "derivatives").glob("*.md")} == {
        "diagrams.md",
        "personas.md",
        "user_stories.md",
    }
    assert (wiki_dir / "notes" / "extraction.jsonl").exists()
    assert (wiki_dir / "reports" / "execution-summary.json").exists()

    summary = json.loads((wiki_dir / "reports" / "execution-summary.json").read_text(encoding="utf-8"))
    assert summary["stage_order"] == ["introspection", "extraction", "aggregation", "derivation"]
    assert summary["directory_summary"]["skipped_counts"]["near_empty_content"] == 1

    for path in (wiki_dir / "sections").glob("*.md"):
        content = path.read_text(encoding="utf-8")
        assert content.startswith("## ")
        assert "\n# " not in content
    user_stories = (wiki_dir / "derivatives" / "user_stories.md").read_text(encoding="utf-8")
    assert "```gherkin" in user_stories
    assert "Given " in user_stories
    assert "When " in user_stories
    assert "Then " in user_stories
