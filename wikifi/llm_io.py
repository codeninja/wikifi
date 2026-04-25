"""Shared helpers for invoking the provider with structured-output safety."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from wikifi.providers.base import Provider, ProviderError

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(raw: str) -> str:
    """Best-effort isolation of a JSON object from a noisy model reply.

    Some models prepend chain-of-thought or wrap the JSON in fences even
    when ``format`` is set. We attempt to locate the first ``{`` ... ``}``
    span. Returning the raw string falls through to the caller's
    ValidationError if no object can be found.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        # Strip ``` ... ``` fence (with optional ```json header).
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    if raw.lstrip().startswith("{"):
        return raw
    match = _JSON_OBJECT_RE.search(raw)
    return match.group(0) if match else raw


def request_structured(
    provider: Provider,
    *,
    prompt: str,
    system: str | None,
    model_cls: type[BaseModel],
    think: bool | str = "high",
    temperature: float = 0.0,
) -> BaseModel:
    """Call the provider in schema mode and validate against ``model_cls``.

    Raises ``ProviderError`` if the response cannot be parsed or
    validated. Honors the rule from the spec: structured-output passes
    require a truthy thinking value to keep schema enforcement reliable.
    """
    schema = model_cls.model_json_schema()
    raw = provider.generate(
        prompt,
        system=system,
        schema=schema,
        think=think,
        temperature=temperature,
    )
    candidate = _extract_json_object(raw)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Provider returned non-JSON for {model_cls.__name__}: {raw[:300]!r}") from exc
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise ProviderError(f"Provider returned JSON that fails {model_cls.__name__} validation: {exc}") from exc


def request_text(
    provider: Provider,
    *,
    prompt: str,
    system: str | None,
    think: bool | str = "high",
    temperature: float = 0.2,
) -> str:
    """Call the provider in free-form mode."""
    return provider.generate(
        prompt,
        system=system,
        schema=None,
        think=think,
        temperature=temperature,
    ).strip()


def strip_top_level_heading(markdown: str) -> str:
    """Demote any leading H1 to H2 to honor the no-top-level-heading rule.

    Some models occasionally emit ``# Section`` despite the prompt. We
    rewrite leading ``# `` lines to ``## `` so the on-disk file stays
    compliant without losing content.
    """
    lines = markdown.splitlines()
    rewritten: list[str] = []
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            indent = line[: len(line) - len(stripped)]
            rewritten.append(f"{indent}## {stripped[2:]}")
        else:
            rewritten.append(line)
        if idx > 200:  # safety bound; nothing in spec needs more
            rewritten.extend(lines[idx + 1 :])
            break
    return "\n".join(rewritten).strip() + "\n"
