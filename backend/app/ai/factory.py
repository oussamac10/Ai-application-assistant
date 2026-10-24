"""AIProviderFactory — selects and instantiates the configured AI provider.

Selection is driven exclusively by the AI_PROVIDER environment variable.
Unsupported provider names are rejected at startup via Settings validation.

Usage in FastAPI dependency injection::

    from fastapi import Depends
    from app.ai.factory import get_ai_provider

    @router.post("/answers")
    async def submit(provider: AIProvider = Depends(get_ai_provider)):
        ...
"""

from __future__ import annotations

import logging

from app.ai.errors import AIProviderConfigurationError
from app.ai.gemini_provider import GeminiAIProvider
from app.ai.mock_provider import AIProvider, MockAIProvider
from app.ai.ollama_provider import OllamaAIProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


def build_provider() -> AIProvider:
    """Build and return the AI provider configured in settings.

    Raises AIProviderConfigurationError for unknown provider names.
    (Settings validation should have caught this earlier, but we guard here
    too so the factory is usable independently of FastAPI startup.)
    """
    name = settings.AI_PROVIDER.lower()

    if name == "mock":
        logger.info("AI provider: MockAIProvider")
        return MockAIProvider()

    if name == "gemini":
        logger.info(
            "AI provider: GeminiAIProvider (model=%s)",
            settings.GEMINI_MODEL,
        )
        return GeminiAIProvider(
            api_key=settings.GEMINI_API_KEY or "",
            model=settings.GEMINI_MODEL,
            base_url=settings.GEMINI_BASE_URL,
            timeout_seconds=settings.GEMINI_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.GEMINI_MAX_RETRIES,
        )

    if name == "ollama":
        logger.info(
            "AI provider: OllamaAIProvider (model=%s, url=%s)",
            settings.OLLAMA_MODEL,
            settings.OLLAMA_BASE_URL,
        )
        return OllamaAIProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout_seconds=settings.OLLAMA_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.OLLAMA_MAX_RETRIES,
        )

    raise AIProviderConfigurationError(
        f"Unknown AI_PROVIDER: '{name}'. Supported values: mock, ollama, gemini"
    )


# Process-level singleton — do not construct one per request
_provider: AIProvider | None = None


def get_provider() -> AIProvider:
    """Return the process-level provider singleton.

    Call this from FastAPI Depends() or service constructors.
    """
    global _provider
    if _provider is None:
        _provider = build_provider()
    return _provider


# FastAPI dependency helper
def get_ai_provider() -> AIProvider:
    return get_provider()
