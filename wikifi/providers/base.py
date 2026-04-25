"""LLM provider protocol.

Wikifi calls a provider in two modes:

1. ``complete_json`` — single shot, model returns a JSON document validated
   against a Pydantic schema. Used for Stage 1 (introspection), Stage 2
   (per-file extraction), and Stage 3 (per-section aggregation).
2. ``complete_text`` — single shot, model returns free markdown. Used when a
   section is best left unstructured (the diagrams pass).

The protocol is deliberately minimal so swapping providers (Ollama → hosted
APIs → mock) is a one-class change.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    name: str
    model: str

    def complete_json(self, *, system: str, user: str, schema: type[T]) -> T:
        """Return an instance of ``schema`` populated by the model."""
        ...

    def complete_text(self, *, system: str, user: str) -> str:
        """Return the model's text response verbatim."""
        ...
