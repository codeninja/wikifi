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
    request_timeout: float = Field(default=300.0, description="Per-request timeout in seconds")
    max_file_bytes: int = Field(default=200_000, description="Skip files larger than this during extraction")
    min_content_bytes: int = Field(
        default=64,
        description="Skip files whose stripped content is shorter than this (avoids thinking runaway on stubs)",
    )
    introspection_depth: int = Field(default=3, description="Tree depth fed to the introspection pass")
    # Thinking mode for reasoning-capable models (Qwen3, DeepSeek-R1, etc.).
    # Default 'low' — Qwen3 ignores `format=<schema>` constraints when
    # thinking is fully disabled and emits free text instead, so we keep a
    # short reasoning trace but cap it to the lowest available level.
    # 'low' / 'medium' / 'high' for Qwen3-style; True for DeepSeek-style;
    # False to opt out entirely (only safe with non-thinking models).
    think: bool | str = Field(default="low", description="Thinking-mode level for reasoning models")


@lru_cache
def get_settings() -> Settings:
    return Settings()
