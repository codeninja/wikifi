from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM Provider
    llm_provider: str = "ollama"
    llm_model: str = "qwen3.6:27b"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: Optional[str] = None
    llm_thinking_level: str = "highest"

    # Extraction Settings
    max_file_size: int = 200_000
    min_content_bytes: int = 64
    
    # Workspace
    wiki_dir: str = ".wikifi"
    
    # Traversal
    exclude_patterns: List[str] = [
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".wikifi",
        "dist",
        "build",
        "*.pyc",
        ".env",
        ".claude",
    ]

settings = Settings()
