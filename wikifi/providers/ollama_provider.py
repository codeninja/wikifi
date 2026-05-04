"""Ollama-backed implementation of LLMProvider.

Uses ``ollama.Client.chat`` with ``format=<json-schema>`` for structured output —
the same mechanism the official ollama-python README recommends for schema
enforcement (see context7 /ollama/ollama-python). Temperature is pinned to 0
for the JSON path so the same input produces the same structured output across
runs; the text path leaves temperature at the model default.

Thinking mode defaults to ``"high"`` for Qwen3-style models. wikifi prefers
output quality over walk wall-time — the derivative-section pass especially
benefits from a fuller reasoning trace. Empirical behavior on local 27B
qwen3-family models:

- ``think=False`` makes Qwen3 ignore the ``format=<schema>`` constraint and
  emit free text (e.g. ``"No findings."``), failing JSON validation.
- ``think="low"`` keeps a short reasoning trace, honors the schema, runs in
  15–60s per call. Use when wall-time matters more than depth.
- ``think="high"`` gives noticeably cleaner abstraction and Gherkin in
  Stage 4 derivatives. Plan for 1–3 minutes per real file on local
  hardware — bump ``timeout`` to ~900s to absorb that.

The walker's ``min_content_bytes`` filter is the companion guard: it
keeps near-empty files (stub ``__init__.py``, one-line configs) from ever
reaching the extractor, where high-think mode would otherwise wander past
the request timeout.

Pass ``True`` for DeepSeek-style reasoning models, ``"low" | "medium" |
"high"`` for Qwen3-style thinking levels, or ``False`` to opt out entirely
(only safe with non-thinking models). See ollama-python docs for the matrix.
"""

from __future__ import annotations

from typing import TypeVar

from ollama import Client
from pydantic import BaseModel

from wikifi.providers.base import ChatMessage, LLMProvider

T = TypeVar("T", bound=BaseModel)

ThinkLevel = bool | str | None


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        *,
        model: str,
        host: str,
        timeout: float = 900.0,
        think: ThinkLevel = "high",
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

    def chat(self, *, system: str, messages: list[ChatMessage]) -> str:
        response = self._client.chat(
            model=self.model,
            messages=[{"role": "system", "content": system}, *messages],
            think=self.think,
        )
        return response.message.content or ""
