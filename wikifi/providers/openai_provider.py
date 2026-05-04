"""OpenAI-backed implementation of :class:`LLMProvider`.

The third provider, alongside :mod:`wikifi.providers.ollama_provider`
(local default) and :mod:`wikifi.providers.anthropic_provider` (hosted
Claude). Selected via ``WIKIFI_PROVIDER=openai`` plus an
``OPENAI_API_KEY``.

Three implementation notes worth flagging:

1. **Structured output via ``chat.completions.parse``.** The Pydantic
   schema is converted to a JSON Schema by the SDK and the model
   returns a pre-validated instance. This is OpenAI's GA path for
   schema-constrained decoding; we don't hand-roll function calls.
2. **Prompt caching is automatic.** Unlike Anthropic, OpenAI does not
   require a ``cache_control`` marker — the API caches identical
   prefixes (≥ 1024 tokens) for ~5–10 minutes automatically. We keep
   the system prompt at message position 0 so wikifi's repeated multi-KB
   extraction prompt is what gets cached.
3. **Reasoning effort.** Reasoning-capable models (o1, o3, o4, gpt-5
   families) accept a ``reasoning_effort`` parameter that mirrors
   wikifi's ``think`` knob. Non-reasoning models silently ignore the
   parameter, so we route the knob through whenever a reasoning level
   is set and skip it on plain models to avoid surfacing a 400 if a
   future SDK starts validating it.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from wikifi.providers.base import ChatMessage, LLMProvider

try:
    import openai
except ImportError as exc:  # pragma: no cover - import error path
    raise ImportError(
        "wikifi.providers.openai_provider requires the `openai` package. "
        "Install via `uv add openai` or include the [hosted] extras."
    ) from exc


T = TypeVar("T", bound=BaseModel)
log = logging.getLogger("wikifi.providers.openai")


# Default model — gpt-4o is the most stable, broadly-available
# structured-output capable model. Override per-walk via ``WIKIFI_MODEL``
# env or ``.wikifi/config.toml`` (e.g. set to a reasoning model like
# ``o3-mini`` or ``gpt-5`` to opt into the reasoning_effort path).
DEFAULT_MODEL = "gpt-4o"

# Default per-call output token cap. wikifi's structured findings are
# small relative to the input; 16K leaves headroom for any of the
# section schemas without crossing the SDK's HTTP timeout guard.
DEFAULT_MAX_TOKENS = 16_000


# Names that match a reasoning-capable model family. We inspect the
# model id by prefix because OpenAI's lineup is too volatile to
# enumerate exactly. Anything matching gets ``reasoning_effort``
# forwarded; anything else has it stripped from the request.
_REASONING_MODEL_RE = re.compile(r"^(o\d|gpt-5)", re.IGNORECASE)


ThinkLevel = bool | str | None


class OpenAIProvider(LLMProvider):
    """Hosted-OpenAI implementation of the wikifi provider protocol."""

    name = "openai"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 900.0,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        think: ThinkLevel = "high",
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.think = think
        if client is not None:
            # Tests pass an injected mock; preserve the duck-typed surface.
            self._client = client
        else:
            api_key = api_key or os.environ.get("OPENAI_API_KEY")
            self._client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            )

    # ------------------------------------------------------------------
    # Provider protocol
    # ------------------------------------------------------------------

    def complete_json(self, *, system: str, user: str, schema: type[T]) -> T:
        """Return a ``schema``-validated Pydantic instance.

        Uses ``chat.completions.parse`` so the SDK runs JSON-Schema-
        constrained decoding and returns the parsed Pydantic model
        directly. The system prompt sits at position 0 so OpenAI's
        automatic prefix cache catches the repeated multi-KB extraction
        prompt across per-file calls.
        """
        try:
            response = self._client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format=schema,
                **self._token_kwargs(),
                **self._reasoning_kwargs(),
            )
        except openai.APIError as exc:
            raise RuntimeError(self.format_api_error(self.name, exc)) from exc

        parsed = _first_parsed(response)
        if parsed is None:
            # Defensive fallback: if the SDK couldn't parse (refusal,
            # truncation), schema-validate the raw JSON text. Keeps the
            # protocol's "raise on failure" contract intact rather than
            # returning a None.
            text = _first_text(response)
            try:
                return schema.model_validate_json(text)
            except Exception as exc:  # pragma: no cover - defensive path
                raise RuntimeError(f"openai provider: empty parsed and validate fallback failed: {exc}") from exc
        return parsed

    def complete_text(self, *, system: str, user: str) -> str:
        """Return the model's free-text response."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **self._token_kwargs(),
                **self._reasoning_kwargs(),
            )
        except openai.APIError as exc:
            raise RuntimeError(self.format_api_error(self.name, exc)) from exc
        return _first_text(response) or ""

    def chat(self, *, system: str, messages: list[ChatMessage]) -> str:
        """Multi-turn chat. The system prompt sits at position 0; the
        running message history follows it."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, *messages],
                **self._token_kwargs(),
                **self._reasoning_kwargs(),
            )
        except openai.APIError as exc:
            raise RuntimeError(self.format_api_error(self.name, exc)) from exc
        return _first_text(response) or ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_reasoning_model(self) -> bool:
        return bool(_REASONING_MODEL_RE.match(self.model))

    def _reasoning_kwargs(self) -> dict[str, Any]:
        """Forward the ``think`` knob as ``reasoning_effort`` only on
        reasoning-capable models. Plain models silently ignore it but
        we still strip it so a future strict validation can't 400 us.
        """
        if not self._is_reasoning_model():
            return {}
        if self.think is False or self.think in {"off", "none"}:
            return {}
        if isinstance(self.think, str) and self.think.lower() in {"low", "medium", "high"}:
            return {"reasoning_effort": self.think.lower()}
        # ``True`` / unrecognized string → adopt SDK default by omitting.
        return {}

    def _token_kwargs(self) -> dict[str, Any]:
        """Output cap. Reasoning models use ``max_completion_tokens``;
        plain chat models use ``max_tokens``. We send the appropriate
        one so neither path 400s on an unrecognized parameter."""
        key = "max_completion_tokens" if self._is_reasoning_model() else "max_tokens"
        return {key: self.max_tokens}


def _first_parsed(response: Any) -> Any:
    """Pull the parsed Pydantic instance out of a parse() response.

    Tolerates the SDK shape (``response.choices[0].message.parsed``)
    and a duck-typed mock (a list of dicts).
    """
    choices = getattr(response, "choices", None) or (response.get("choices") if isinstance(response, dict) else None)
    if not choices:
        return None
    first = choices[0]
    message = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
    if message is None:
        return None
    parsed = getattr(message, "parsed", None) or (message.get("parsed") if isinstance(message, dict) else None)
    return parsed


def _first_text(response: Any) -> str:
    """Pull the first text content out of a chat-completion response."""
    choices = getattr(response, "choices", None) or (response.get("choices") if isinstance(response, dict) else None)
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None) or (first.get("message") if isinstance(first, dict) else None)
    if message is None:
        return ""
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    return content or ""
