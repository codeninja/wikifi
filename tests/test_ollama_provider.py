"""Unit tests for OllamaProvider with httpx mocked via httpx.MockTransport."""

from __future__ import annotations

import httpx
import pytest

from wikifi.providers.base import ProviderError
from wikifi.providers.ollama import OllamaProvider


def _patch_httpx(monkeypatch, handler):
    transport = httpx.MockTransport(handler)

    def fake_get(url, **kwargs):
        with httpx.Client(transport=transport) as client:
            return client.get(url, **kwargs)

    def fake_post(url, **kwargs):
        with httpx.Client(transport=transport) as client:
            return client.post(url, **kwargs)

    monkeypatch.setattr("wikifi.providers.ollama.httpx.get", fake_get)
    monkeypatch.setattr("wikifi.providers.ollama.httpx.post", fake_post)


def test_healthcheck_passes_when_model_present(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "qwen3:1b"}]})

    _patch_httpx(monkeypatch, handler)
    OllamaProvider(model="qwen3:1b").healthcheck()


def test_healthcheck_fails_when_model_missing(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "other"}]})

    _patch_httpx(monkeypatch, handler)
    with pytest.raises(ProviderError, match="not available"):
        OllamaProvider(model="qwen3:1b").healthcheck()


def test_healthcheck_unreachable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    _patch_httpx(monkeypatch, handler)
    with pytest.raises(ProviderError, match="Cannot reach Ollama"):
        OllamaProvider().healthcheck()


def test_generate_returns_message_content(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={"message": {"content": "hello world"}, "done": True},
        )

    _patch_httpx(monkeypatch, handler)
    out = OllamaProvider(model="m").generate("hi")
    assert out == "hello world"


def test_generate_passes_schema(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = request.read()
        return httpx.Response(200, json={"message": {"content": "{}"}, "done": True})

    _patch_httpx(monkeypatch, handler)
    OllamaProvider(model="m").generate("p", schema={"type": "object"})
    assert b'"format":' in captured["payload"]


def test_generate_empty_completion_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": ""}, "done_reason": "stop"})

    _patch_httpx(monkeypatch, handler)
    with pytest.raises(ProviderError, match="empty completion"):
        OllamaProvider(model="m").generate("p")


def test_generate_http_error_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    _patch_httpx(monkeypatch, handler)
    with pytest.raises(ProviderError, match="HTTP 500"):
        OllamaProvider(model="m").generate("p")
