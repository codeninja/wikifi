from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from wikifi.constants import SUPPORTED_PROVIDERS
from wikifi.models import Settings


class ProviderError(RuntimeError):
    pass


class UnsupportedProviderError(ProviderError):
    pass


class LLMProvider(ABC):
    provider_id: str

    @abstractmethod
    def generate_text(self, *, system: str, prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_json(self, *, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


@dataclass
class OllamaProvider(LLMProvider):
    settings: Settings

    provider_id: str = "ollama"

    def generate_text(self, *, system: str, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        return self._request(payload)

    def generate_json(self, *, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "system": system,
            "prompt": f"{prompt}\n\nReturn only JSON matching this schema:\n{json.dumps(schema, sort_keys=True)}",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        response = self._request(payload)
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Provider returned invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("Provider returned JSON that is not an object.")
        return parsed

    def _request(self, payload: dict[str, Any]) -> str:
        request = urllib.request.Request(
            self.settings.ollama_host.rstrip("/") + "/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.request_timeout) as response:
                body = response.read().decode("utf-8")
        except (OSError, urllib.error.URLError) as exc:
            raise ProviderError(f"Ollama provider request failed: {exc}") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Ollama provider returned invalid response JSON: {exc}") from exc

        text = parsed.get("response")
        if not isinstance(text, str):
            raise ProviderError("Ollama provider response did not include a text response.")
        return text.strip()


def build_provider(settings: Settings) -> LLMProvider:
    if settings.provider not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise UnsupportedProviderError(
            f"Unsupported provider '{settings.provider}'. Supported providers for this release: {supported}."
        )
    return OllamaProvider(settings=settings)
