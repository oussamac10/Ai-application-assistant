"""Deterministic translation provider for tests and offline development.

Marks text with the target language rather than returning it unchanged: an
unmarked string would make a genuinely-missing translation indistinguishable
from a successful one, so tests asserting "this label was translated into
Arabic" would pass even when nothing happened.
"""

from __future__ import annotations

from app.translation.base import (
    TranslationRequest,
    TranslationResponse,
    TranslationUsage,
)


class MockTranslationProvider:
    provider_name = "mock"

    def __init__(self, fail_ids: set[int] | None = None) -> None:
        # Lets a test exercise the per-item recovery path without a stub
        # provider of its own.
        self._fail_ids = fail_ids or set()
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        self.calls.append(
            (request.target_language, tuple(item.text for item in request.items))
        )
        translations = {
            item.id: f"[{request.target_language}] {item.text}"
            for item in request.items
            if item.id not in self._fail_ids
        }
        return TranslationResponse(
            translations_by_id=translations,
            usage=TranslationUsage(
                provider_name=self.provider_name,
                target_language=request.target_language,
                request_count=1 if request.items else 0,
                translated_character_count=sum(
                    len(item.text) for item in request.items
                ),
                # The mock "detects" whatever it was told to assume, so the
                # metadata path is exercised without inventing a language.
                detected_source_languages=(
                    (request.source_language or request.assumed_source_language,)
                    if request.items
                    else ()
                ),
            ),
        )

    async def health_check(self) -> bool:
        return True
