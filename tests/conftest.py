"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wikifi.config import Settings
from wikifi.providers.fake import FakeProvider


@pytest.fixture
def settings_factory():
    def _make(**overrides: Any) -> Settings:
        defaults = {
            "provider": "fake",
            "model": "fake-model",
            "ollama_host": "http://localhost:11434",
            "request_timeout": 5.0,
            "max_file_bytes": 4_000,
            "min_content_bytes": 16,
            "introspection_depth": 2,
            "think": "high",
            "wiki_dir_name": ".wikifi",
        }
        defaults.update(overrides)
        return Settings(**defaults)

    return _make


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a tiny synthetic repo with a mix of in-scope and skipped files."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "billing.py").write_text(
        """
        # billing module
        def charge(account_id: str, amount: int) -> None:
            \"\"\"Charge a customer's account when an order is placed.\"\"\"
            ...
        def refund(account_id: str, amount: int) -> None:
            \"\"\"Reverse a previously-issued charge for a customer.\"\"\"
            ...
        """.strip(),
        encoding="utf-8",
    )
    (tmp_path / "src" / "__init__.py").write_text("\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "# Demo\nA demo billing service.\n" + ("filler ") * 50,
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("console.log('do not read me');\n" * 5, encoding="utf-8")
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (tmp_path / "ignored.log").write_text("garbage data\n" * 200, encoding="utf-8")
    (tmp_path / "asset.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    return tmp_path


@pytest.fixture
def deterministic_provider() -> FakeProvider:
    """A FakeProvider whose default handler emits sensible structured/text replies."""

    def _default(prompt: str, system: str | None, schema: dict[str, Any] | None) -> str:
        if schema is None:
            # Free-form synthesis fallback — return a plausible markdown shell.
            return (
                "## Synthesized Section\n\n"
                "The available evidence describes a documentation pipeline.\n\n"
                "### Documented Gaps\nNot enough evidence to expand further.\n"
            )
        # Structured-output dispatch by prompt content.
        if "JSON object with these fields" in prompt or "primary_languages" in prompt:
            return json.dumps(
                {
                    "primary_languages": ["python"],
                    "inferred_purpose": "A documentation pipeline that turns code into a wiki.",
                    "classification_rationale": "Manifests indicate a Python project.",
                    "in_scope_globs": ["src/**/*.py"],
                    "out_of_scope_globs": ["**/__init__.py"],
                    "notable_manifests": ["README.md"],
                }
            )
        if "JSON schema requirements" in prompt or "role_summary" in prompt:
            return json.dumps(
                {
                    "role_summary": "Captures the responsibility for billing operations within the system.",
                    "findings": [
                        {
                            "section": "capabilities",
                            "finding": "Provides charge and refund capability for customer accounts.",
                        },
                        {
                            "section": "domains",
                            "finding": "Resides in the billing bounded context of the financial domain.",
                        },
                    ],
                    "skip_reason": None,
                }
            )
        # Fallback structured: return minimal valid JSON.
        return json.dumps({"role_summary": "n/a", "findings": [], "skip_reason": "no signal"})

    return FakeProvider(default_handler=_default)
