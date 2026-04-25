"""Ollama-backed implementation of LLMProvider.

Uses ``ollama.Client.chat`` with ``format=<json-schema>`` for structured output —
the same mechanism the official ollama-python README recommends for schema
enforcement (see context7 /ollama/ollama-python). Temperature is pinned to 0
for the JSON path so the same input produces the same structured output across
runs; the text path leaves temperature at the model default.
"""

from __future__ import annotations

from typing import TypeVar

from ollama import Client
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class OllamaProvider:
    name = "ollama"

    def __init__(self, *, model: str, host: str, timeout: float = 300.0) -> None:
        self.model = model
        self.host = host
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
        )
        return schema.model_validate_json(response.message.content)

    def complete_text(self, *, system: str, user: str) -> str:
        response = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.message.content or ""
