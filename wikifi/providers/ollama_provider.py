"""Ollama-backed implementation of LLMProvider.

Uses ``ollama.Client.chat`` with ``format=<json-schema>`` for structured output —
the same mechanism the official ollama-python README recommends for schema
enforcement (see context7 /ollama/ollama-python). Temperature is pinned to 0
for the JSON path so the same input produces the same structured output across
runs; the text path leaves temperature at the model default.

Thinking mode defaults to ``"low"`` for Qwen3-style models. Empirically:

- ``think=False`` makes Qwen3 ignore the ``format=<schema>`` constraint and
  emit free text (e.g. ``"No findings."``), failing JSON validation.
- ``think=True``/unset (default-high) sends the model into long chain-of-
  thought traces that hit the request timeout on tiny inputs.
- ``think="low"`` keeps a short reasoning trace, honors the schema, and
  keeps per-call latency in the 15–60s range on local hardware.

Pass ``True`` for DeepSeek-style reasoning models, ``"low" | "medium" |
"high"`` for Qwen3-style thinking levels, or ``False`` to opt out entirely
(only safe with non-thinking models). See ollama-python docs for the matrix.
"""

from __future__ import annotations

from typing import TypeVar

from ollama import Client
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

ThinkLevel = bool | str | None


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        model: str,
        host: str,
        timeout: float = 300.0,
        think: ThinkLevel = "low",
    ) -> None:
        self.model = model
        self.host = host
        self.think = think
        self._client = Client(host=host, timeout=timeout)

    def complete_json(self, *, system: str, user: str, schema: type[T]) -> T:
        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            format=schema.model_json_schema(),
            options={"temperature": 0},
            think=self.think,
        )
        return schema.model_validate_json(response.message.content)

    def complete_text(self, *, system: str, user: str) -> str:
        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            think=self.think,
        )
        return response.message.content or ""
