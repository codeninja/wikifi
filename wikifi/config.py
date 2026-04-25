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
    introspection_depth: int = Field(default=3, description="Tree depth fed to the introspection pass")


@lru_cache
def get_settings() -> Settings:
    return Settings()
