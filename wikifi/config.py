"""Runtime settings loaded from environment / .env.

Defaults assume a local Ollama server with qwen3.6:27b. Override any field via
WIKIFI_* env vars or a .env file in the target project's CWD.
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

    provider: str = Field(default="ollama", description="LLM provider id; only 'ollama' in v1")
    model: str = Field(default="qwen3.6:27b", description="Model identifier passed to the provider")
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama HTTP endpoint")
    request_timeout: float = Field(default=900.0, description="Per-request timeout in seconds")
    max_file_bytes: int = Field(default=200_000, description="Skip files larger than this during extraction")
    min_content_bytes: int = Field(
        default=64,
        description="Skip files whose stripped content is shorter than this (avoids thinking runaway on stubs)",
    )
    introspection_depth: int = Field(default=3, description="Tree depth fed to the introspection pass")
    # Thinking mode for reasoning-capable models (Qwen3, DeepSeek-R1, etc.).
    # Default 'high' — wikifi prioritizes wiki quality over walk wall-time.
    # Higher thinking levels produce noticeably better domain abstraction and
    # cleaner Gherkin in the derivative pass; expect 1–3 minutes per real
    # file on a local 27B model. The min_content_bytes guard keeps the
    # thinking-runaway-on-stubs failure mode at bay.
    # Accepted values: 'low' / 'medium' / 'high' (Qwen3-style); True
    # (DeepSeek-style); False to opt out entirely (only safe with non-
    # thinking models — Qwen3 ignores `format=<schema>` when thinking is off).
    think: bool | str = Field(default="high", description="Thinking-mode level for reasoning models")


@lru_cache
def get_settings() -> Settings:
    return Settings()
