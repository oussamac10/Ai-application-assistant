"""Resolves the configured translation providers.

Mirrors the field-detection provider factory (Phase 11/14): business logic
depends on the `TranslationProvider` interface, and exactly one place knows
which concrete implementation the configuration selects.

The primary provider and the fallback are resolved independently, so a
deployment can run `azure` with an `ollama` safety net, `ollama` alone, or
`mock` in tests, without any caller changing.
"""

from __future__ import annotations

import logging

from app.ai.mock_provider import AIProvider
from app.translation.base import TranslationProvider
from app.translation.errors import TranslationConfigurationError
from app.translation.providers.azure import AzureTranslatorProvider
from app.translation.providers.gemini import GeminiTranslationProvider
from app.translation.providers.mock import MockTranslationProvider
from app.translation.providers.ollama import OllamaTranslationProvider

logger = logging.getLogger(__name__)

SUPPORTED_TRANSLATION_PROVIDERS = ("mock", "ollama", "azure", "gemini")

# Values meaning "no fallback provider". Source text is still the final
# fallback inside the service, so this never leaves a document blocked.
_NO_PROVIDER = frozenset({"", "none", "null", "off"})


def build_translation_provider(
    name: str,
    ai_provider: AIProvider | None = None,
) -> TranslationProvider:
    """Builds one provider by name.

    `ai_provider` is required for `ollama` and `gemini`, which delegate to the
    existing `AIProvider` batch contract rather than reimplementing the
    prompt, parsing and repair logic that Phase 14 already got right.
    """
    normalized = (name or "").strip().lower()

    if normalized == "mock":
        return MockTranslationProvider()
    if normalized == "azure":
        return AzureTranslatorProvider()
    if normalized == "ollama":
        if ai_provider is None:
            raise TranslationConfigurationError(
                "The ollama translation provider requires an AI provider."
            )
        return OllamaTranslationProvider(ai_provider)
    if normalized == "gemini":
        if ai_provider is None:
            raise TranslationConfigurationError(
                "The gemini translation provider requires an AI provider."
            )
        return GeminiTranslationProvider(ai_provider)

    raise TranslationConfigurationError(
        f"Unknown translation provider '{name}'. Supported values: "
        f"{list(SUPPORTED_TRANSLATION_PROVIDERS)}."
    )


def build_fallback_translation_provider(
    name: str,
    ai_provider: AIProvider | None = None,
) -> TranslationProvider | None:
    """Like `build_translation_provider`, but `none` (or empty) means no
    fallback rather than an error."""
    if (name or "").strip().lower() in _NO_PROVIDER:
        return None
    return build_translation_provider(name, ai_provider)
