"""Centralized runtime configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ThinkLevel = Literal["high", "medium", "low", "true", "false"]


class Settings(BaseSettings):
    """Runtime settings for wikifi.

    Environment variables (prefix ``WIKIFI_``) take effect, but a local
    ``.env`` file in the target repository overrides them — local config
    has precedence over environment defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="WIKIFI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    provider: Literal["ollama", "fake"] = "ollama"
    model: str = "qwen3.6:27b"
    ollama_host: str = "http://localhost:11434"
    request_timeout: float = 900.0
    max_file_bytes: int = 200_000
    min_content_bytes: int = 64
    introspection_depth: int = 3
    think: ThinkLevel = "high"

    wiki_dir_name: str = ".wikifi"

    extractor_concurrency: int = Field(
        default=1,
        description="Per-file extraction is sequential by default to keep deterministic ordering.",
    )

    def think_payload(self) -> bool | str:
        """Translate WIKIFI_THINK into the value Ollama's API expects."""
        if self.think == "true":
            return True
        if self.think == "false":
            return False
        return self.think


def load_settings(target: Path | None = None) -> Settings:
    """Load settings, honoring a target-repo-local ``.env`` if present.

    The active working directory is briefly considered so that ``Settings``
    picks up an ``.env`` co-located with the target repo.
    """
    if target is None:
        return Settings()
    env_file = target / ".env"
    if env_file.is_file():
        return Settings(_env_file=str(env_file))  # type: ignore[call-arg]
    return Settings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
