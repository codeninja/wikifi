from wikifi.config import settings
from wikifi.provider.base import LLMProvider
from wikifi.provider.ollama import OllamaProvider

def get_provider() -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            thinking_level=settings.llm_thinking_level
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
