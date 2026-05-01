"""OpenAIProvider tests.

The HTTP transport is mocked via the ``client=`` injection point so the
test never touches the network. The point is to lock in the wikifi
contract: structured output via ``chat.completions.parse``, the
reasoning-effort routing for reasoning vs. plain models, the
``max_tokens`` vs ``max_completion_tokens`` swap, and APIError →
RuntimeError mapping.
"""

from __future__ import annotations

from types import SimpleNamespace

import openai
import pytest
from pydantic import BaseModel

from wikifi.providers.openai_provider import OpenAIProvider


class _Echo(BaseModel):
    value: str


class _StubClient:
    """Minimal stand-in for ``openai.OpenAI``.

    Exposes ``chat.completions.parse`` and ``chat.completions.create``
    via the same ``SimpleNamespace`` shape the real SDK uses.
    """

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
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(parse=self._parse, create=self._create),
        )

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


def _api_error(message: str = "boom", request_id: str = "req_abc") -> openai.APIError:
    """Construct an APIError without going through the real httpx wiring."""
    err = openai.APIError.__new__(openai.APIError)
    err.message = message
    err.request_id = request_id
    err.args = (message,)
    return err


def _parse_response(parsed):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed, content=""))],
    )


def _text_response(text: str | None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text, parsed=None))],
    )


# ---------------------------------------------------------------------------
# complete_json
# ---------------------------------------------------------------------------


def test_complete_json_returns_parsed_pydantic_instance():
    parsed = _Echo(value="hello")
    client = _StubClient(parse_response=_parse_response(parsed))
    provider = OpenAIProvider(model="gpt-4o", client=client, think="high")

    result = provider.complete_json(system="SYS", user="USR", schema=_Echo)

    assert result == parsed
    call = client.parse_calls[0]
    assert call["model"] == "gpt-4o"
    assert call["response_format"] is _Echo
    assert call["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USR"},
    ]
    # gpt-4o is non-reasoning → max_tokens, not max_completion_tokens.
    assert "max_tokens" in call
    assert "max_completion_tokens" not in call
    # think="high" must NOT leak through on a non-reasoning model.
    assert "reasoning_effort" not in call


def test_complete_json_falls_back_to_validate_json_when_parsed_missing():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=None, content='{"value": "fallback"}'))],
    )
    client = _StubClient(parse_response=response)
    provider = OpenAIProvider(client=client)
    out = provider.complete_json(system="s", user="u", schema=_Echo)
    assert out == _Echo(value="fallback")


def test_complete_json_raises_runtime_error_on_api_error():
    client = _StubClient(raise_on_parse=_api_error("rate-limited", "req_xyz"))
    provider = OpenAIProvider(client=client)
    with pytest.raises(RuntimeError) as info:
        provider.complete_json(system="s", user="u", schema=_Echo)
    assert "req_xyz" in str(info.value)
    assert "rate-limited" in str(info.value)


# ---------------------------------------------------------------------------
# complete_text + chat
# ---------------------------------------------------------------------------


def test_complete_text_extracts_first_message_content():
    client = _StubClient(create_response=_text_response("hi"))
    provider = OpenAIProvider(client=client)
    assert provider.complete_text(system="s", user="u") == "hi"


def test_complete_text_returns_empty_when_content_none():
    client = _StubClient(create_response=_text_response(None))
    provider = OpenAIProvider(client=client)
    assert provider.complete_text(system="s", user="u") == ""


def test_chat_prepends_system_and_returns_content():
    client = _StubClient(create_response=_text_response("reply"))
    provider = OpenAIProvider(client=client)
    out = provider.chat(
        system="SYS",
        messages=[
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "first reply"},
            {"role": "user", "content": "second"},
        ],
    )
    assert out == "reply"
    call = client.create_calls[0]
    assert call["messages"][0] == {"role": "system", "content": "SYS"}
    assert call["messages"][-1] == {"role": "user", "content": "second"}
    assert len(call["messages"]) == 4


# ---------------------------------------------------------------------------
# Reasoning model routing
# ---------------------------------------------------------------------------


def test_reasoning_model_forwards_reasoning_effort_and_uses_completion_tokens():
    """o-series + gpt-5 models should receive ``reasoning_effort`` and
    ``max_completion_tokens`` instead of ``max_tokens``."""
    client = _StubClient(create_response=_text_response("x"))
    provider = OpenAIProvider(model="o3-mini", client=client, think="medium")
    provider.complete_text(system="s", user="u")
    call = client.create_calls[0]
    assert call["reasoning_effort"] == "medium"
    assert "max_completion_tokens" in call
    assert "max_tokens" not in call


def test_reasoning_model_strips_effort_when_think_is_off():
    client = _StubClient(create_response=_text_response("x"))
    provider = OpenAIProvider(model="gpt-5", client=client, think=False)
    provider.complete_text(system="s", user="u")
    call = client.create_calls[0]
    assert "reasoning_effort" not in call
    # Reasoning model still uses max_completion_tokens regardless of think.
    assert "max_completion_tokens" in call


def test_plain_model_does_not_forward_reasoning_effort():
    client = _StubClient(create_response=_text_response("x"))
    provider = OpenAIProvider(model="gpt-4o", client=client, think="high")
    provider.complete_text(system="s", user="u")
    call = client.create_calls[0]
    assert "reasoning_effort" not in call


# ---------------------------------------------------------------------------
# Token-knob translation table
# ---------------------------------------------------------------------------


def test_reasoning_kwargs_translation_table():
    """Lock the (model, think) → request mapping so the contract is testable."""
    client = _StubClient(create_response=_text_response("x"))
    cases = [
        # Reasoning-capable model: each level forwards through
        ("o3-mini", "low", {"reasoning_effort": "low"}),
        ("o3-mini", "medium", {"reasoning_effort": "medium"}),
        ("o3-mini", "high", {"reasoning_effort": "high"}),
        ("o3-mini", True, {}),  # SDK default
        ("o3-mini", False, {}),  # disabled
        ("o3-mini", "off", {}),
        # Plain model: never forwards
        ("gpt-4o", "high", {}),
        ("gpt-4o", "low", {}),
        ("gpt-4o", False, {}),
    ]
    for model, think, expected_extras in cases:
        provider = OpenAIProvider(model=model, client=client, think=think)
        client.create_calls.clear()
        provider.complete_text(system="s", user="u")
        call = client.create_calls[-1]
        if "reasoning_effort" in expected_extras:
            assert call.get("reasoning_effort") == expected_extras["reasoning_effort"], (
                f"model={model} think={think!r}: want {expected_extras}"
            )
        else:
            assert "reasoning_effort" not in call, f"model={model} think={think!r}: must not forward effort"
