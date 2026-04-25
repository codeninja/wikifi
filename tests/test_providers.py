from __future__ import annotations

import json

import pytest

from wikifi.config import Settings
from wikifi.factory import build_provider
from wikifi.providers.base import ProviderError
from wikifi.providers.fake import FakeProvider


def test_fake_provider_returns_canned_response():
    provider = FakeProvider(responses=["hello"])
    assert provider.generate("anything") == "hello"
    assert provider.calls[0]["prompt"] == "anything"


def test_fake_provider_callable_response():
    provider = FakeProvider(responses=[lambda p, s, sch: f"echo:{p}"])
    assert provider.generate("ping") == "echo:ping"


def test_fake_provider_raises_when_exhausted():
    provider = FakeProvider()
    with pytest.raises(ProviderError):
        provider.generate("anything")


def test_fake_provider_returns_schema_response_unchecked():
    """FakeProvider mirrors a real provider's permissive contract; JSON
    validation is the caller's responsibility (see llm_io.request_structured).
    """
    provider = FakeProvider(responses=["not json"])
    assert provider.generate("p", schema={"type": "object"}) == "not json"


def test_fake_provider_default_handler():
    provider = FakeProvider(default_handler=lambda p, s, sch: json.dumps({"ok": True}))
    text = provider.generate("p", schema={"type": "object"})
    assert json.loads(text) == {"ok": True}


def test_factory_unsupported_provider():
    settings = Settings(provider="ollama")
    settings.provider = "openai"  # type: ignore[assignment]
    with pytest.raises(ProviderError):
        build_provider(settings)


def test_factory_returns_ollama_for_ollama_setting():
    settings = Settings(provider="ollama", model="m", ollama_host="http://x", request_timeout=5.0)
    provider = build_provider(settings)
    assert provider.name == "ollama"
