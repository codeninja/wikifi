"""AnthropicProvider tests.

The HTTP transport is mocked via the ``client=`` injection point so the
test never touches the network. The point is to lock in the wikifi
contract: prompt caching on the system prompt, structured output via
``messages.parse``, and APIError → RuntimeError mapping.
"""

from __future__ import annotations

from types import SimpleNamespace

import anthropic
import pytest
from pydantic import BaseModel

from wikifi.providers.anthropic_provider import AnthropicProvider


class _Echo(BaseModel):
    value: str


class _StubClient:
    """Minimal stand-in for ``anthropic.Anthropic`` exposing ``messages``."""

    def __init__(
        self,
        *,
        parse_response=None,
        create_response=None,
        raise_on_parse: Exception | None = None,
        raise_on_create: Exception | None = None,
    ) -> None:
        self.parse_calls: list[dict] = []
        self.create_calls: list[dict] = []
        self._parse_response = parse_response
        self._create_response = create_response
        self._raise_on_parse = raise_on_parse
        self._raise_on_create = raise_on_create
        self.messages = SimpleNamespace(parse=self._parse, create=self._create)

    def _parse(self, **kwargs):
        self.parse_calls.append(kwargs)
        if self._raise_on_parse is not None:
            raise self._raise_on_parse
        return self._parse_response

    def _create(self, **kwargs):
        self.create_calls.append(kwargs)
        if self._raise_on_create is not None:
            raise self._raise_on_create
        return self._create_response


def _api_error(message: str = "boom", request_id: str = "req_abc") -> anthropic.APIError:
    """Build an APIError without going through the real httpx wiring."""
    err = anthropic.APIError.__new__(anthropic.APIError)
    err.message = message
    err.request_id = request_id
    err.args = (message,)
    return err


def test_complete_json_passes_cache_control_and_returns_pydantic():
    parsed = _Echo(value="hello")
    response = SimpleNamespace(parsed_output=parsed, content=[])
    client = _StubClient(parse_response=response)

    provider = AnthropicProvider(model="claude-opus-4-7", client=client, think="high")
    result = provider.complete_json(system="SYS", user="USR", schema=_Echo)

    assert result == parsed
    call = client.parse_calls[0]
    assert call["model"] == "claude-opus-4-7"
    assert call["output_format"] is _Echo
    assert call["messages"] == [{"role": "user", "content": "USR"}]
    # System prompt must be a list with a cache_control marker.
    system = call["system"]
    assert isinstance(system, list)
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert system[0]["text"] == "SYS"
    # think="high" → adaptive thinking + effort.
    assert call["thinking"] == {"type": "adaptive"}
    assert call["output_config"] == {"effort": "high"}


def test_complete_json_falls_back_to_validate_json_when_parsed_output_missing():
    response = SimpleNamespace(
        parsed_output=None,
        content=[SimpleNamespace(type="text", text='{"value": "fallback"}')],
    )
    client = _StubClient(parse_response=response)
    provider = AnthropicProvider(client=client)
    out = provider.complete_json(system="s", user="u", schema=_Echo)
    assert out == _Echo(value="fallback")


def test_complete_json_raises_runtime_error_on_api_error():
    client = _StubClient(raise_on_parse=_api_error("rate-limited", "req_xyz"))
    provider = AnthropicProvider(client=client)
    with pytest.raises(RuntimeError) as info:
        provider.complete_json(system="s", user="u", schema=_Echo)
    assert "req_xyz" in str(info.value)
    assert "rate-limited" in str(info.value)


def test_complete_text_extracts_first_text_block():
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text="hi")])
    client = _StubClient(create_response=response)
    provider = AnthropicProvider(client=client)
    assert provider.complete_text(system="s", user="u") == "hi"


def test_complete_text_returns_empty_when_no_text_block():
    response = SimpleNamespace(content=[])
    client = _StubClient(create_response=response)
    provider = AnthropicProvider(client=client)
    assert provider.complete_text(system="s", user="u") == ""


def test_chat_forwards_messages_and_caches_system():
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text="hello back")])
    client = _StubClient(create_response=response)
    provider = AnthropicProvider(client=client, think=False)
    out = provider.chat(
        system="SYS",
        messages=[{"role": "user", "content": "first"}],
    )
    assert out == "hello back"
    call = client.create_calls[0]
    assert call["messages"] == [{"role": "user", "content": "first"}]
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    # think=False → thinking disabled, no effort.
    assert call["thinking"] == {"type": "disabled"}
    assert "output_config" not in call


def test_thinking_kwargs_translation_table():
    """Lock the think-knob → request mapping so the contract is testable."""
    client = _StubClient(create_response=SimpleNamespace(content=[]))
    cases = [
        ("low", {"thinking": {"type": "adaptive"}, "output_config": {"effort": "low"}}),
        ("medium", {"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}),
        ("high", {"thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}}),
        ("max", {"thinking": {"type": "adaptive"}, "output_config": {"effort": "max"}}),
        (True, {"thinking": {"type": "adaptive"}}),
        (False, {"thinking": {"type": "disabled"}}),
        ("off", {"thinking": {"type": "disabled"}}),
    ]
    for think, expected in cases:
        provider = AnthropicProvider(client=client, think=think)
        # Reset the recorded calls between cases.
        client.create_calls.clear()
        provider.complete_text(system="s", user="u")
        call = client.create_calls[-1]
        for key, value in expected.items():
            assert call.get(key) == value, f"think={think!r}: expected {key}={value}"
        if "output_config" not in expected:
            assert "output_config" not in call


def test_cache_system_prompt_off_returns_plain_string():
    response = SimpleNamespace(content=[])
    client = _StubClient(create_response=response)
    provider = AnthropicProvider(client=client, cache_system_prompt=False)
    provider.complete_text(system="SYS", user="u")
    assert client.create_calls[0]["system"] == "SYS"


def test_complete_json_raises_diagnostic_on_fully_empty_response():
    """Empty parsed_output AND empty text → emit a diagnostic with knobs.

    Locks in the user-reported failure mode where adaptive thinking
    consumes the entire ``max_tokens`` budget and the structured
    output block never lands. The replacement RuntimeError must
    surface ``stop_reason``, ``output_tokens``, and ``max_tokens`` so
    operators see which knob to turn (raise max_tokens, lower think
    effort) instead of the original cryptic "Invalid JSON: EOF"
    pydantic validation error.
    """
    response = SimpleNamespace(
        parsed_output=None,
        content=[],
        stop_reason="max_tokens",
        usage=SimpleNamespace(output_tokens=16_000),
    )
    client = _StubClient(parse_response=response)
    provider = AnthropicProvider(client=client, max_tokens=16_000)
    with pytest.raises(RuntimeError) as info:
        provider.complete_json(system="s", user="u", schema=_Echo)
    msg = str(info.value)
    # Operator-facing diagnostic — names the knobs, not the SDK internals.
    assert "max_tokens=16000" in msg
    assert "output_tokens=16000" in msg
    assert "stop_reason='max_tokens'" in msg
    assert "raise max_tokens" in msg.lower() or "lower think" in msg.lower()
