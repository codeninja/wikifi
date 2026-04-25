"""Ollama HTTP backend for the wikifi provider abstraction."""

from __future__ import annotations

import json
from typing import Any

import httpx

from wikifi.providers.base import Provider, ProviderError


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(
        self,
        *,
        host: str = "http://localhost:11434",
        model: str = "qwen3.6:27b",
        timeout: float = 900.0,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def healthcheck(self) -> None:
        url = f"{self.host}/api/tags"
        try:
            response = httpx.get(url, timeout=10.0)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Cannot reach Ollama at {self.host}: {exc}. Is `ollama serve` running?") from exc
        if response.status_code != 200:
            raise ProviderError(f"Ollama health probe failed: HTTP {response.status_code} from {url}")
        models = {entry.get("name") for entry in response.json().get("models", [])}
        if self.model not in models:
            raise ProviderError(
                f"Model '{self.model}' is not available on {self.host}. "
                f"Available: {sorted(m for m in models if m)}. Pull with `ollama pull {self.model}`."
            )

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        think: bool | str = "high",
        temperature: float = 0.0,
    ) -> str:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
            "think": think,
        }
        if schema is not None:
            payload["format"] = schema

        url = f"{self.host}/api/chat"
        try:
            response = httpx.post(url, json=payload, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc

        if response.status_code != 200:
            raise ProviderError(f"Ollama returned HTTP {response.status_code}: {response.text[:500]}")

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Ollama returned non-JSON body: {exc}") from exc

        message = body.get("message") or {}
        content = message.get("content") or ""
        if not isinstance(content, str) or not content.strip():
            raise ProviderError(f"Ollama returned an empty completion. done_reason={body.get('done_reason')!r}")
        return content
