from __future__ import annotations

import json

import pytest

from wikifi.models import Settings
from wikifi.providers import OllamaProvider, UnsupportedProviderError, build_provider


class FakeResponse:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_build_provider_enforces_single_supported_provider() -> None:
    assert isinstance(build_provider(Settings(provider="ollama")), OllamaProvider)

    with pytest.raises(UnsupportedProviderError, match="Unsupported provider 'openai'"):
        build_provider(Settings(provider="openai"))


def test_ollama_provider_parses_text_and_json_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        body = json.loads(request.data.decode("utf-8"))
        if body.get("format") == "json":
            return FakeResponse({"response": json.dumps({"role_summary": "Analyzes intent."})})
        return FakeResponse({"response": "Narrative output"})

    monkeypatch.setattr("wikifi.providers.urllib.request.urlopen", fake_urlopen)
    provider = OllamaProvider(Settings(request_timeout=7))

    text = provider.generate_text(system="system", prompt="prompt")
    parsed = provider.generate_json(system="system", prompt="prompt", schema={"type": "object"})

    assert text == "Narrative output"
    assert parsed == {"role_summary": "Analyzes intent."}
    assert len(requests) == 2
    assert requests[0][1] == 7
