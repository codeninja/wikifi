"""Runtime settings loaded from environment / .env.

Defaults assume a local Ollama server with qwen3.6:27b. Override any field via
WIKIFI_* env vars or a .env file in the target project's CWD.

Hosted providers are opt-in:
- ``WIKIFI_PROVIDER=anthropic`` (plus ``ANTHROPIC_API_KEY``)
- ``WIKIFI_PROVIDER=openai`` (plus ``OPENAI_API_KEY``)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
