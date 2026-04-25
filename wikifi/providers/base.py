"""Provider contract: one method, two modes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ProviderError(RuntimeError):
    """Raised when an LLM provider fails to deliver a usable response."""


class Provider(ABC):
    """Abstract LLM provider.

    Implementations expose a single ``generate`` entry point that supports
    two modes:

    * **Free-form**: ``schema=None`` returns the model's text reply as-is.
    * **Structured**: passing a JSON-schema dict (typically ``Model.model_json_schema()``)
      forces the backend to emit a JSON object that conforms, and the raw
      JSON string is returned.

    All implementations honor ``think`` to carry the reasoning level
    (``"high"`` / ``"medium"`` / ``"low"`` / ``True`` / ``False``).
    """

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        think: bool | str = "high",
        temperature: float = 0.0,
    ) -> str:  # pragma: no cover - interface
        """Return text (or JSON-as-text when ``schema`` is supplied)."""

    def healthcheck(self) -> None:  # pragma: no cover - default no-op
        """Optional connectivity probe. Override in concrete backends."""
        return None
