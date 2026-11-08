"""Factory for instantiating embedding providers based on environment configuration."""

from __future__ import annotations

import logging

from app.ai.embedding.gemini import GeminiEmbeddingProvider
from app.ai.embedding.mock import MockEmbeddingProvider
from app.ai.embedding.protocol import EmbeddingProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

_singleton_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Returns an EmbeddingProvider instance based on system settings.

    In test or mock mode, returns deterministic MockEmbeddingProvider (€0 cost).
    When GEMINI_API_KEY is present and provider is gemini/cloud, returns GeminiEmbeddingProvider.
    """
    global _singleton_provider
    if _singleton_provider is not None:
        return _singleton_provider

    provider_name = (settings.AI_PROVIDER or "mock").lower()

    if provider_name == "mock" or not settings.GEMINI_API_KEY:
        _singleton_provider = MockEmbeddingProvider()
        return _singleton_provider

    if provider_name in ("gemini", "vertex"):
        _singleton_provider = GeminiEmbeddingProvider(
            api_key=settings.GEMINI_API_KEY,
            model=getattr(settings, "EMBEDDING_MODEL", "text-embedding-004"),
        )
        return _singleton_provider

    # Fallback to mock
    _singleton_provider = MockEmbeddingProvider()
    return _singleton_provider


def reset_embedding_provider() -> None:
    """Testing helper: resets singleton embedding provider."""
    global _singleton_provider
    _singleton_provider = None
