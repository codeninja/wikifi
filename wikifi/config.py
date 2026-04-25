import json
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    root_path: str = Field(default=".")
    workspace_path: str = Field(default=".wikifi")
    max_file_size: int = Field(default=200000)
    min_content_length: int = Field(default=64)
    exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            ".git",
            "__pycache__",
            "node_modules",
            "venv",
            ".venv",
            "dist",
            "build",
            ".pytest_cache",
            ".ruff_cache",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".DS_Store",
            ".wikifi",  # Exclude the entire workspace to prevent recursive reading
        ]
    )
    llm_model: str = Field(default="ollama/llama3")
    llm_api_key: str | None = Field(default=None)

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    settings = Settings()

    # Load overrides from .wikifi/config.json if it exists
    # Local configuration files strictly override environment-level variables.
    config_file = Path(settings.workspace_path) / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                overrides = json.load(f)

            # Create a new settings object with overrides
            settings = Settings(**{**settings.model_dump(), **overrides})
        except Exception:
            pass

    return settings
