"""Anthropic-backed implementation of :class:`LLMProvider`.

This is the premium / hosted path. Wikifi's pipeline reuses the same
multi-KB system prompt across hundreds of per-file extraction calls; the
defining design choice here is to mark that prompt with
``cache_control: {"type": "ephemeral"}`` so subsequent calls served by
the same cache breakpoint pay ~10% of the input price (cache read) instead
of full price every time. Without that, hosted Anthropic is uneconomical
on a 10k-file codebase walk; with it, the cost story competes with
local Ollama at materially better extraction quality.

Three design notes worth flagging:

1. **Structured output via ``messages.parse``.** The Pydantic schema is
   converted to JSON Schema by the SDK and the model returns a
   pre-validated instance. This is the SDK's recommended path for
   structured outputs (see ``claude-api`` skill, *Structured Outputs*) —
   we don't hand-roll tool_use blocks for this.
2. **Adaptive thinking + effort.** Opus 4.7 (the recommended default)
   supports only adaptive thinking and exposes ``effort`` for depth.
   Sampling parameters (``temperature``, ``top_p``, ``top_k``) are
   removed on 4.7 and would 400 if sent — we omit them entirely. The
   ``think`` knob mirrors the Ollama provider's interface so the rest
   of the codebase doesn't branch on provider.
3. **Errors map to ``RuntimeError``.** The aggregator/extractor/deriver
   already catch broad ``Exception`` per call; mapping
   ``anthropic.APIError`` (and friends) into a plain ``RuntimeError``
   with the request id keeps the pipeline's existing fallback paths
   working unchanged.
"""

from __future__ import annotations

import logging
import os
from typing import Any, TypeVar

from pydantic import BaseModel

from wikifi.providers.base import ChatMessage, LLMProvider

try:  # the dep is declared in pyproject.toml, but importing lazily yields
    # a clearer error if a user installs without extras.
    import anthropic
except ImportError as exc:  # pragma: no cover - import error path
    raise ImportError(
        "wikifi.providers.anthropic_provider requires the `anthropic` package. "
        "Install via `uv add anthropic` or include the [hosted] extras."
    ) from exc


T = TypeVar("T", bound=BaseModel)
log = logging.getLogger("wikifi.providers.anthropic")


# Default model — opus 4.7 is the most capable for migration-grade
# domain extraction. Override per-walk via `WIKIFI_MODEL` env or
# `.wikifi/config.toml`.
DEFAULT_MODEL = "claude-opus-4-7"

# Default per-call max output tokens. Adaptive thinking at ``effort=high``
# can consume substantial output budget on its own; if ``max_tokens`` is too
# tight, the model burns its allowance on the thinking trace and the
# structured-output block comes back empty (``parsed_output is None`` and
# no text content). 32K leaves comfortable headroom for any of the wiki
# section schemas while staying under the SDK's non-streaming HTTP timeout
# guard. Premium-effort callers ("xhigh"/"max") should bump higher and
# enable streaming — see Anthropic's Opus 4.7 migration notes.
DEFAULT_MAX_TOKENS = 32_000


ThinkLevel = bool | str | None


class AnthropicProvider(LLMProvider):
    """Hosted-Claude implementation of the wikifi provider protocol."""

    name = "anthropic"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        timeout: float = 900.0,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        think: ThinkLevel = "high",
        cache_system_prompt: bool = True,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.think = think
        self.cache_system_prompt = cache_system_prompt
        if client is not None:
            # Tests pass an injected mock; preserve the duck-typed surface.
            self._client = client
        else:
            api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    # ------------------------------------------------------------------
    # Provider protocol
    # ------------------------------------------------------------------

    def complete_json(self, *, system: str, user: str, schema: type[T]) -> T:
        """Return a ``schema``-validated Pydantic instance.

        Uses ``messages.parse`` so the SDK runs JSON-Schema-constrained
        decoding and returns the parsed Pydantic model directly. The
        system prompt is wrapped in a single text block with
        ``cache_control`` so successive per-file calls hit the prompt
        cache.
        """
        try:
            response = self._client.messages.parse(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._render_system(system),
                messages=[{"role": "user", "content": user}],
                output_format=schema,
                **self._thinking_kwargs(),
            )
        except anthropic.APIError as exc:
            raise RuntimeError(self.format_api_error(self.name, exc)) from exc

        parsed = getattr(response, "parsed_output", None)
        if parsed is not None:
            return parsed  # type: ignore[return-value]
        # The SDK couldn't parse a structured instance. Try the raw text
        # block (covers refusals where the model emitted text rather than
        # the structured form) before raising.
        text = _first_text(response)
        if text:
            try:
                return schema.model_validate_json(text)
            except Exception as exc:  # pragma: no cover - defensive path
                raise RuntimeError(
                    f"anthropic provider: parsed_output missing and JSON validation of response text failed: {exc}"
                ) from exc
        # No parsed output and no text — typically the thinking trace
        # consumed the entire output budget. Surface stop_reason and
        # usage so the caller knows whether to raise ``max_tokens``,
        # lower ``effort``, or look at a refusal.
        raise RuntimeError(_empty_response_message(response, self.max_tokens))

    def complete_text(self, *, system: str, user: str) -> str:
        """Return the model's free-text response."""
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._render_system(system),
                messages=[{"role": "user", "content": user}],
                **self._thinking_kwargs(),
            )
        except anthropic.APIError as exc:
            raise RuntimeError(self.format_api_error(self.name, exc)) from exc
        return _first_text(response) or ""

    def chat(self, *, system: str, messages: list[ChatMessage]) -> str:
        """Multi-turn chat. The system prompt is cached; the running
        message history follows it (and is therefore not cached itself
        beyond the prefix-match window — see the prompt-caching guide
        in the ``claude-api`` skill)."""
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self._render_system(system),
                messages=list(messages),
                **self._thinking_kwargs(),
            )
        except anthropic.APIError as exc:
            raise RuntimeError(self.format_api_error(self.name, exc)) from exc
        return _first_text(response) or ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _render_system(self, system: str) -> list[dict[str, Any]] | str:
        """Wrap ``system`` in a single text block with ``cache_control``.

        Returning a list (not a string) is what enables the cache mark.
        Wikifi's per-file system prompt is large and identical across
        every Stage 2 / Stage 3 / Stage 4 call — the cache hit on the
        2nd-Nth request is the entire cost story for hosted runs.
        """
        if not self.cache_system_prompt:
            return system
        return [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def _thinking_kwargs(self) -> dict[str, Any]:
        """Translate ``think`` into Anthropic's adaptive-thinking config.

        - ``False`` / ``"off"`` / ``"none"`` → thinking disabled.
        - ``"low"`` / ``"medium"`` / ``"high"`` / ``"max"`` → adaptive
          thinking with the corresponding ``effort``. Wikifi defaults
          to ``"high"`` since the walk is bounded; bump to ``"max"`` for
          intelligence-critical migrations.
        - ``True`` / unspecified string → adaptive thinking, no
          ``effort`` override (SDK default).
        """
        if self.think is False or self.think in {"off", "none"}:
            return {"thinking": {"type": "disabled"}}
        if isinstance(self.think, str) and self.think.lower() in {"low", "medium", "high", "xhigh", "max"}:
            return {
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": self.think.lower()},
            }
        return {"thinking": {"type": "adaptive"}}


def _first_text(response: Any) -> str:
    """Pull the first text block out of a Messages response.

    Tolerates the SDK shape (``response.content`` is a list of typed
    blocks) and a duck-typed mock (a list of dicts).
    """
    content = getattr(response, "content", None)
    if not content:
        return ""
    for block in content:
        block_type = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
        if block_type == "text":
            text = getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else None)
            if text:
                return text
    return ""


def _empty_response_message(response: Any, max_tokens: int) -> str:
    """Diagnose an empty structured response with stop_reason + usage.

    The dominant cause is adaptive thinking consuming the entire
    ``max_tokens`` budget before the structured output block is
    produced. Surface the operational knobs (``max_tokens``,
    ``effort``) so the caller sees the fix at the failure site.
    """
    stop_reason = getattr(response, "stop_reason", None)
    usage = getattr(response, "usage", None)
    output_tokens = getattr(usage, "output_tokens", None) if usage is not None else None
    parts = [
        "anthropic provider: empty structured response (no parsed_output, no text block)",
        f"stop_reason={stop_reason!r}",
        f"output_tokens={output_tokens}",
        f"max_tokens={max_tokens}",
    ]
    if stop_reason == "max_tokens" or (output_tokens is not None and output_tokens >= max_tokens):
        parts.append("hint: thinking likely consumed the budget — raise max_tokens or lower think/effort")
    elif stop_reason == "refusal":
        parts.append("hint: model refused; the input may need rewording")
    return " | ".join(parts)
