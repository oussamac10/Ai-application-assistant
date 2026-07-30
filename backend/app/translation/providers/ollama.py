"""Ollama as a `TranslationProvider`.

Wraps the Phase 14 `AIProvider.translate_output_batch` contract so the local
model stays usable — as the default provider when Azure is not configured, and
as the fallback when Azure fails. Keeping it means a developer with no Azure
credentials, and a deployment whose Azure resource is down, both still get
translated questions.

The local model cannot detect a source language reliably, so this provider
translates from `assumed_source_language` and reports that as the detected
language rather than guessing. Real detection is Azure's contribution.

Chunking and concurrency live here rather than in the service, because they
are a property of *this* backend: a small local model follows a long
multi-item instruction poorly, so the work is split into
`AI_TRANSLATION_BATCH_SIZE` pieces and run with bounded concurrency. Azure has
the opposite characteristics and chunks differently. A failed chunk costs only
that chunk — its ids are simply absent, and the service recovers them.
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


class OllamaTranslationProvider:
    provider_name = "ollama"

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
            # This provider cannot detect, so it can only act on the assumed
            # source language — and under that assumption there is nothing to
            # translate. Returning the text unchanged is honest and free;
            # asking a local model to translate en -> en is neither.
            return TranslationResponse(
                translations_by_id={item.id: item.text for item in request.items},
                usage=TranslationUsage(
                    provider_name=self.provider_name,
                    target_language=request.target_language,
                    # No outbound request was made, so no request is counted.
                    request_count=0,
                    status_class="none",
                    detected_source_languages=(source,),
                    # Asserted from configuration, not detected. Flagging it
                    # is what stops this assumption overriding a real answer.
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
                    # One chunk failing must not lose the others. Its ids stay
                    # absent and the service recovers exactly those.
                    logger.warning(
                        "Ollama translation chunk failed: target_language=%s "
                        "items=%d error=%s",
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
            # Nothing at all came back: report it as a provider failure so the
            # service can fall back rather than silently producing no text.
            raise TranslationProviderError(
                "The local model could not translate any item in this batch.",
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
                # Asserted, not detected — see the module docstring.
                detected_source_languages=(source,),
                # This provider cannot detect a language; it reports the one
                # it was told to assume. See the module docstring.
                source_language_is_detected=False,
                status_class="2xx",
            ),
        )

    async def health_check(self) -> bool:
        try:
            return await self._ai_provider.health_check()
        except AIProviderError:
            return False
