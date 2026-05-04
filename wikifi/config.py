"""Runtime settings loaded from environment / .env / target's .wikifi/config.toml.

Defaults assume a local Ollama server with qwen3.6:27b. Override any field via
WIKIFI_* env vars, a .env file in the target project's CWD, or by writing
provider/model entries into ``<target>/.wikifi/config.toml`` (the file
``wikifi init`` scaffolds — and what callers expect to be authoritative for
that wiki).

Resolution order, highest precedence first:

1. ``<target>/.wikifi/config.toml``
2. ``WIKIFI_*`` environment variables (and ``.env``)
3. Field defaults

The wiki's own ``config.toml`` wins over per-session env vars: a wiki
initialized for a hosted backend should still drive its own runs even
when the user happens to have ``WIKIFI_PROVIDER=ollama`` exported in
their shell. This matches the contract printed at the top of every
generated ``config.toml`` ("overrides WIKIFI_* environment variables
when present").

Hosted providers are opt-in:
- ``WIKIFI_PROVIDER=anthropic`` (plus ``ANTHROPIC_API_KEY``)
- ``WIKIFI_PROVIDER=openai`` (plus ``OPENAI_API_KEY``)
"""

from __future__ import annotations

import logging
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("wikifi.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WIKIFI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = Field(
        default="ollama",
        description="LLM provider id; 'ollama' (default), 'anthropic', or 'openai'",
    )
    model: str = Field(default="qwen3.6:27b", description="Model identifier passed to the provider")
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama HTTP endpoint")
    request_timeout: float = Field(default=900.0, description="Per-request timeout in seconds")
    # Absolute skip threshold for the walker. Files larger than this are
    # treated as vendored/generated noise and never read. Real source files —
    # even monolithic ones — should fit comfortably under this; the extractor
    # chunks anything bigger than ``chunk_size_bytes`` into overlapping
    # windows rather than truncating.
    max_file_bytes: int = Field(
        default=2_000_000,
        description="Walker skip threshold; files larger are dropped as noise",
    )
    # Per-LLM-call window size. Files larger than this are split into
    # overlapping chunks (one call each). 150 KB fits comfortably in a 32K
    # context model after prompt overhead while still consuming most source
    # files in a single call.
    chunk_size_bytes: int = Field(
        default=150_000,
        description="Per-LLM-call chunk size when splitting large files",
    )
    chunk_overlap_bytes: int = Field(
        default=8_000,
        description="Bytes shared between adjacent chunks to preserve cross-boundary context",
    )
    min_content_bytes: int = Field(
        default=64,
        description="Skip files whose stripped content is shorter than this (avoids thinking runaway on stubs)",
    )
    introspection_depth: int = Field(default=3, description="Tree depth fed to the introspection pass")
    # Thinking mode for reasoning-capable models (Qwen3, DeepSeek-R1, Anthropic).
    # Default 'high' — wikifi prioritizes wiki quality over walk wall-time.
    # On Anthropic, this maps to adaptive thinking + the equivalent
    # ``effort`` level (low/medium/high/max).
    think: bool | str = Field(default="high", description="Thinking-mode level for reasoning models")

    # ----- Premium pipeline knobs -----

    use_cache: bool = Field(
        default=True,
        description=(
            "Reuse the per-file extraction + per-section aggregation caches across walks. "
            "Disable to force a clean re-walk."
        ),
    )
    use_graph: bool = Field(
        default=True,
        description=(
            "Build an import/reference graph and feed each file's neighborhood into the "
            "extraction prompt. Disable to fall back to per-file isolated extraction."
        ),
    )
    use_specialized_extractors: bool = Field(
        default=True,
        description=(
            "Route schema files (SQL, OpenAPI, Protobuf, GraphQL, migrations) through "
            "deterministic extractors that bypass the LLM."
        ),
    )
    review_derivatives: bool = Field(
        default=False,
        description=(
            "Run the critic + reviser loop on derivative sections (personas, user stories, "
            "diagrams). Adds 2 LLM calls per derivative section but materially improves "
            "groundedness. Off by default to keep walk wall-time predictable."
        ),
    )
    review_min_score: int = Field(
        default=7,
        description="Minimum critic score below which the reviser is invoked.",
    )
    use_surgical_edits: bool = Field(
        default=True,
        description=(
            "When some findings change in a section but most are unchanged, edit the cached "
            "section body in place around the delta instead of rewriting from scratch. "
            "Preserves established prose and citation numbering. Disable to force the prior "
            "(pre-Plan-B) behavior of full rewrites on any note change."
        ),
    )
    surgical_edit_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Maximum churn ratio (added+removed findings divided by live findings) that "
            "still routes to the surgical-edit path. Above this a section falls back to "
            "full re-aggregation, which produces a cleaner narrative when the underlying "
            "evidence has shifted substantially."
        ),
    )

    # ----- Anthropic provider knobs -----

    anthropic_api_key: str | None = Field(
        default=None,
        description=("Explicit Anthropic API key. Falls back to ANTHROPIC_API_KEY in the environment when unset."),
    )
    anthropic_max_tokens: int = Field(
        default=32_000,
        description=(
            "Per-call output token cap for the Anthropic provider. "
            "Adaptive thinking at ``effort=high`` can consume substantial "
            "output budget; 32K leaves comfortable headroom for the wiki "
            "section schemas while staying under the SDK's non-streaming "
            "HTTP timeout guard. Premium-effort callers (xhigh/max) "
            "should bump higher and enable streaming."
        ),
    )

    # ----- OpenAI provider knobs -----

    openai_api_key: str | None = Field(
        default=None,
        description=("Explicit OpenAI API key. Falls back to OPENAI_API_KEY in the environment when unset."),
    )
    openai_base_url: str | None = Field(
        default=None,
        description=("Explicit OpenAI base URL (for Azure-OpenAI / proxies). Defaults to api.openai.com."),
    )
    openai_max_tokens: int = Field(
        default=16_000,
        description="Per-call output token cap for the OpenAI provider.",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """Drop the cached :class:`Settings` instance so env changes take effect.

    Used by tests that mutate ``WIKIFI_*`` env vars between cases.
    """
    get_settings.cache_clear()


# Field names a wiki's ``config.toml`` is allowed to override. We accept
# only the fields ``wikifi init`` writes today (provider, model,
# ollama_host) so a stale or hand-edited config can't silently start
# overriding behavior the user didn't sign up for.
_TARGET_CONFIG_FIELDS: frozenset[str] = frozenset({"provider", "model", "ollama_host"})


def load_target_settings(target: Path) -> Settings:
    """Return :class:`Settings` for a wiki at ``target``.

    Reads ``<target>/.wikifi/config.toml`` (when present) and layers
    its values on top of the env-derived defaults — the wiki's own
    config wins over per-session env vars, matching the contract
    printed at the top of every generated ``config.toml``.

    Without this, ``wikifi report --score <target>`` (and the other
    target-aware commands) would build a provider from the process-wide
    defaults regardless of what the target wiki was actually
    initialized with — fine when target equals CWD, but wrong when the
    user is operating against another project's wiki.
    """
    base = get_settings()
    overrides = _read_target_config(target)
    if not overrides:
        return base
    effective: dict[str, Any] = {field: value for field, value in overrides.items() if field in _TARGET_CONFIG_FIELDS}
    if not effective:
        return base
    return base.model_copy(update=effective)


def _read_target_config(target: Path) -> dict[str, Any]:
    """Parse ``<target>/.wikifi/config.toml``; return ``{}`` on any failure."""
    config_path = target / ".wikifi" / "config.toml"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("could not read %s: %s; falling back to env-only settings", config_path, exc)
        return {}
