"""LLM provider abstract base class.

Wikifi calls a provider in three modes:

1. ``complete_json`` — single shot, model returns a JSON document validated
   against a Pydantic schema. Used for Stage 1 (introspection), Stage 2
   (per-file extraction), and Stage 3 (per-section aggregation).
2. ``complete_text`` — single shot, model returns free markdown. Used when a
   section is best left unstructured (the diagrams pass).
3. ``chat`` — multi-turn, model receives a system prompt and a running
   message list. Used by the ``wikifi chat`` REPL where conversation history
   carries between turns.

The base class is deliberately minimal so swapping providers (Ollama → hosted
APIs → mock) is a one-class change. Concrete subclasses inherit nominally so
``isinstance(p, LLMProvider)`` works and ``ABC`` enforces the three call
surfaces at construction time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ChatMessage(TypedDict):
    role: str
    content: str


class LLMProvider(ABC):
    """Nominal base class every backend implements.

    Subclasses set the class-level ``name`` (provider id) and assign
    ``self.model`` in ``__init__``. The three abstract methods are the
    full contract — wikifi never calls anything else on a provider.
    """

    name: str
    model: str

    @abstractmethod
    def complete_json(self, *, system: str, user: str, schema: type[T]) -> T:
        """Return an instance of ``schema`` populated by the model."""

    @abstractmethod
    def complete_text(self, *, system: str, user: str) -> str:
        """Return the model's text response verbatim."""

    @abstractmethod
    def chat(self, *, system: str, messages: list[ChatMessage]) -> str:
        """Run a multi-turn exchange and return the assistant's next reply."""

    @staticmethod
    def format_api_error(provider_name: str, exc: Exception) -> str:
        """Render a vendor APIError with the request id, when present.

        Shared by hosted providers (Anthropic, OpenAI) so the diagnostic
        format is consistent across backends.
        """
        request_id = getattr(exc, "request_id", None)
        msg = getattr(exc, "message", None) or str(exc)
        if request_id:
            return f"{provider_name} provider failed ({request_id}): {msg}"
        return f"{provider_name} provider failed: {msg}"
