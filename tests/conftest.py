"""Shared pytest fixtures.

The MockProvider lets every test exercise the real Stage 1/2/3 code paths
without an Ollama server. Tests register canned responses keyed by the schema
class so the same provider can serve introspection, extraction, and
aggregation calls in a single walk.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TypeVar

import pytest
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Mock LLM provider
# ---------------------------------------------------------------------------


class MockProvider:
    """Test double for ``LLMProvider`` driven by per-schema response queues."""

    name = "mock"
    model = "mock-model"

    def __init__(
        self,
        *,
        json_responses: dict[type[BaseModel], Iterable[BaseModel]] | None = None,
        text_responses: Iterable[str] | None = None,
        json_factory: Callable[[type[BaseModel], str, str], BaseModel] | None = None,
    ) -> None:
        self._json_queues: dict[type[BaseModel], list[BaseModel]] = {
            cls: list(queue) for cls, queue in (json_responses or {}).items()
        }
        self._text_queue: list[str] = list(text_responses or [])
        self._json_factory = json_factory
        self.json_calls: list[tuple[type[BaseModel], str, str]] = []
        self.text_calls: list[tuple[str, str]] = []

    def complete_json(self, *, system: str, user: str, schema: type[T]) -> T:
        self.json_calls.append((schema, system, user))
        if self._json_factory is not None:
            return self._json_factory(schema, system, user)  # type: ignore[return-value]
        queue = self._json_queues.get(schema)
        if not queue:
            raise AssertionError(f"MockProvider has no queued response for {schema.__name__}")
        return queue.pop(0)  # type: ignore[return-value]

    def complete_text(self, *, system: str, user: str) -> str:
        self.text_calls.append((system, user))
        if not self._text_queue:
            raise AssertionError("MockProvider has no queued text response")
        return self._text_queue.pop(0)


@pytest.fixture
def mock_provider_factory() -> Callable[..., MockProvider]:
    return MockProvider


# ---------------------------------------------------------------------------
# Filesystem fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mini_target(tmp_path: Path) -> Path:
    """Lay out a tiny synthetic project with a manifest, source, and noise.

    Used as the target of walker / introspection / orchestrator tests so the
    real codebase isn't a test dependency.
    """
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fakeapp"\nversion = "0.0.1"\ndescription = "demo"\n'
    )
    (tmp_path / "README.md").write_text("# fakeapp\n\nA demo target for tests.\n")

    src = tmp_path / "src" / "fakeapp"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "domain.py").write_text(
        "class Order:\n"
        "    def __init__(self, customer, items):\n"
        "        self.customer = customer\n"
        "        self.items = items\n"
    )
    (src / "api.py").write_text(
        "def place_order(customer, items):\n"
        "    return {'customer': customer, 'items': items}\n"
    )

    noise = tmp_path / "node_modules" / "leftpad"
    noise.mkdir(parents=True)
    (noise / "index.js").write_text("module.exports = function(){};\n")

    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "stale.pyc").write_bytes(b"\x00\x01")

    (tmp_path / ".gitignore").write_text("dist/\n")
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "build.tar").write_bytes(b"build artifact")

    return tmp_path
