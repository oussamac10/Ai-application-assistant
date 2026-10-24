"""Gemini as a `TranslationProvider`.

Wraps `GeminiAIProvider.translate_output_batch` to implement the `TranslationProvider`
contract, offering fast multilingual translation via the Gemini Flash API.
"""

from __future__ import annotations

import asyncio
import logging
import time

from app.ai.errors import AIProviderError
from app.ai.mock_provider import AIProvider
from app.ai.schemas import BatchTranslationItem
from app.ai.schemas import BatchTranslationRequest as AIBatchTranslationRequest
from app.core.config import settings
from app.translation.base import (
    TranslationItem,
    TranslationRequest,
    TranslationResponse,
    TranslationUsage,
)
from app.translation.errors import TranslationProviderError

logger = logging.getLogger(__name__)


class GeminiTranslationProvider:
    provider_name = "gemini"

    def __init__(self, ai_provider: AIProvider) -> None:
        self._ai_provider = ai_provider

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        if not request.items:
            return TranslationResponse(
                translations_by_id={},
                usage=TranslationUsage(
                    provider_name=self.provider_name,
                    target_language=request.target_language,
                ),
            )

        source = request.source_language or request.assumed_source_language
        if source == request.target_language:
            return TranslationResponse(
                translations_by_id={item.id: item.text for item in request.items},
                usage=TranslationUsage(
                    provider_name=self.provider_name,
                    target_language=request.target_language,
                    request_count=0,
                    status_class="none",
                    detected_source_languages=(source,),
                    source_language_is_detected=False,
                ),
            )

        started = time.perf_counter()

        items = list(request.items)
        batch_size = max(settings.AI_TRANSLATION_BATCH_SIZE, 1)
        chunks = [
            items[start : start + batch_size]
            for start in range(0, len(items), batch_size)
        ]
        semaphore = asyncio.Semaphore(max(settings.AI_TRANSLATION_CONCURRENCY, 1))

        async def run(chunk: list[TranslationItem]) -> dict[int, str]:
            async with semaphore:
                try:
                    result = await self._ai_provider.translate_output_batch(
                        AIBatchTranslationRequest(
                            items=[
                                BatchTranslationItem(id=item.id, text=item.text)
                                for item in chunk
                            ],
                            sourceLanguage=source,
                            targetLanguage=request.target_language,
                        )
                    )
                except AIProviderError as exc:
                    logger.warning(
                        "Gemini translation chunk failed: target_language=%s items=%d error=%s",
                        request.target_language,
                        len(chunk),
                        type(exc).__name__,
                    )
                    return {}
                return dict(result.translations_by_id)

        translations: dict[int, str] = {}
        for chunk_result in await asyncio.gather(*(run(chunk) for chunk in chunks)):
            translations.update(chunk_result)

        if not translations and items:
            raise TranslationProviderError(
                "Gemini could not translate any item in this batch.",
                "translation_failed",
            )

        latency = time.perf_counter() - started
        return TranslationResponse(
            translations_by_id=translations,
            usage=TranslationUsage(
                provider_name=self.provider_name,
                target_language=request.target_language,
                request_count=len(chunks),
                translated_character_count=sum(
                    len(item.text) for item in request.items
                ),
                latency_seconds=latency,
                detected_source_languages=(source,),
                source_language_is_detected=False,
                status_class="2xx",
            ),
        )

    async def health_check(self) -> bool:
        try:
            return await self._ai_provider.health_check()
        except AIProviderError:
            return False
