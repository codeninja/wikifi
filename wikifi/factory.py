"""Factory wiring config to a concrete provider."""

from __future__ import annotations

from wikifi.config import Settings
from wikifi.providers.base import Provider, ProviderError
from wikifi.providers.ollama import OllamaProvider


def build_provider(settings: Settings) -> Provider:
    """Return a Provider instance honoring the configured backend.

    Single-provider constraint: only ``ollama`` is supported in v1. Any
    other ``provider`` value raises ``ProviderError`` so the pipeline can
    surface the misconfiguration without partially executing.
    """
    if settings.provider == "ollama":
        return OllamaProvider(
            host=settings.ollama_host,
            model=settings.model,
            timeout=settings.request_timeout,
        )
    if settings.provider == "fake":  # pragma: no cover - tests inject directly
        from wikifi.providers.fake import FakeProvider

        return FakeProvider()
    raise ProviderError(f"Unsupported provider '{settings.provider}'. Only 'ollama' is supported in v1.")
