"""Shared, provider-agnostic text-translation helper.

Used by every question-presentation code path that needs to translate a
piece of already-resolved source text into a target language via the AI
provider's generic `translate_output` — dynamically detected field labels
and options (app/field_detection/question_bridge.py) and the reusable
question resolver's AI-translation fallback tier
(app/questions/resolver.py). Centralizing this here means there is exactly
one place that decides how AI translation failures are handled, and one
place logging its outcome — not two divergent implementations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.ai.errors import AIProviderError
from app.ai.mock_provider import AIProvider
from app.ai.schemas import TranslationRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TextTranslation:
    """Structured result of translating one piece of text."""

    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    # Whether the translation actually came back from the provider. Callers
    # cannot infer this by comparing the two texts: a legitimate translation
    # is often identical to its source (a German option label translated into
    # German, a proper noun, "IBAN"), and treating that as a failure both
    # mis-reports the outcome and needlessly skips caching it.
    succeeded: bool = True


async def translate_text(
    ai_provider: AIProvider,
    text: str,
    source_language: str,
    target_language: str,
) -> TextTranslation:
    """Translates `text` for display in `target_language`, preserving it
    untouched as `source_text`.

    No AI call is made when the languages already match. On any AI failure
    the original text is returned as a safe fallback so callers are never
    blocked — only the outcome (never the text itself) is logged.
    """
    if source_language == target_language:
        return TextTranslation(text, text, source_language, target_language)

    try:
        result = await ai_provider.translate_output(
            TranslationRequest(
                text=text,
                sourceLanguage=source_language,
                targetLanguage=target_language,
            )
        )
        logger.info(
            "Text translated: provider=%s source_language=%s target_language=%s "
            "status=success",
            type(ai_provider).__name__,
            source_language,
            target_language,
        )
        return TextTranslation(
            text, result.translated_text, source_language, target_language
        )
    except AIProviderError as exc:
        logger.warning(
            "Text translation failed, falling back to source text: "
            "provider=%s source_language=%s target_language=%s status=failure "
            "error=%s",
            type(ai_provider).__name__,
            source_language,
            target_language,
            type(exc).__name__,
        )
        return TextTranslation(
            text, text, source_language, target_language, succeeded=False
        )
