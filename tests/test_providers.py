"""Provider tests.

The Ollama provider's HTTP wiring is exercised by mocking ``ollama.Client.chat``
so the test does not require a running Ollama server. The point of these
tests is to lock in our schema-passing contract: ``format=schema_dict`` and
``temperature=0`` for the JSON path.
"""

from __future__ import annotations

from types import SimpleNamespace

from pydantic import BaseModel

from wikifi.providers.ollama_provider import OllamaProvider


class _Echo(BaseModel):
    value: str


def _stub_chat_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(content=content))


def test_ollama_provider_complete_json_uses_schema_format(monkeypatch):
    captured: dict = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return _stub_chat_response('{"value": "hello"}')

    provider = OllamaProvider(model="m", host="http://h")
    monkeypatch.setattr(provider._client, "chat", fake_chat)

    result = provider.complete_json(system="sys", user="usr", schema=_Echo)
    assert result == _Echo(value="hello")
    assert captured["model"] == "m"
    assert captured["format"] == _Echo.model_json_schema()
    assert captured["options"] == {"temperature": 0}
    assert captured["messages"][0] == {"role": "system", "content": "sys"}
    assert captured["messages"][1] == {"role": "user", "content": "usr"}
    # Default think="high" is forwarded to the client — wikifi prioritizes
    # wiki quality over per-call latency. See provider docstring for the
    # rationale and the failure modes at the boundary settings.
    assert captured["think"] == "high"


def test_ollama_provider_forwards_custom_think_level(monkeypatch):
    captured: dict = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return _stub_chat_response('{"value": "x"}')

    provider = OllamaProvider(model="m", host="http://h", think=False)
    monkeypatch.setattr(provider._client, "chat", fake_chat)

    provider.complete_json(system="s", user="u", schema=_Echo)
    assert captured["think"] is False


def test_ollama_provider_complete_text_returns_message_content(monkeypatch):
    provider = OllamaProvider(model="m", host="http://h")
    monkeypatch.setattr(provider._client, "chat", lambda **kwargs: _stub_chat_response("free text"))
    assert provider.complete_text(system="s", user="u") == "free text"


def test_ollama_provider_complete_text_handles_none(monkeypatch):
    provider = OllamaProvider(model="m", host="http://h")
    monkeypatch.setattr(provider._client, "chat", lambda **kwargs: _stub_chat_response(None))
    assert provider.complete_text(system="s", user="u") == ""
