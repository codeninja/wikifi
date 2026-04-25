"""Deterministic in-process provider used by tests and offline runs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wikifi.providers.base import Provider, ProviderError

PromptHandler = Callable[[str, str | None, dict[str, Any] | None], str]


class FakeProvider(Provider):
    """Maps inbound prompts to canned responses.

    Two layering options are supported:

    * ``responses``: a list consumed FIFO. Each element is either a
      string (returned as-is) or a callable receiving
      ``(prompt, system, schema)`` and returning a string.
    * ``default_handler``: invoked when ``responses`` is exhausted.
    """

    name = "fake"

    def __init__(
        self,
        *,
        responses: list[str | PromptHandler] | None = None,
        default_handler: PromptHandler | None = None,
    ) -> None:
        self._responses: list[str | PromptHandler] = list(responses or [])
        self._default = default_handler
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        think: bool | str = "high",
        temperature: float = 0.0,
    ) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "system": system,
                "schema": schema,
                "think": think,
                "temperature": temperature,
            }
        )

        response: str
        if self._responses:
            entry = self._responses.pop(0)
            response = entry(prompt, system, schema) if callable(entry) else entry
        elif self._default is not None:
            response = self._default(prompt, system, schema)
        else:
            raise ProviderError("FakeProvider has no canned response left to return.")

        # Note: we do NOT validate JSON here. Real providers can return
        # chatter around the JSON object — caller-side helpers (llm_io) own
        # extraction and validation. Keeping FakeProvider permissive lets
        # tests reproduce that behaviour.
        return response
