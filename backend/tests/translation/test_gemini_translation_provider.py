"""Tests for GeminiTranslationProvider — unit tests with mocked AIProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.schemas import BatchTranslationResult
from app.translation.base import TranslationItem, TranslationRequest
from app.translation.providers.gemini import GeminiTranslationProvider


@pytest.mark.asyncio
async def test_gemini_translation_provider_batch() -> None:
    mock_ai = MagicMock()
    mock_ai.translate_output_batch = AsyncMock(
        return_value=BatchTranslationResult(
            translationsById={1: "Nom de famille", 2: "Prénom"}
        )
    )

    provider = GeminiTranslationProvider(mock_ai)
    request = TranslationRequest(
        items=(
            TranslationItem(id=1, text="Last Name"),
            TranslationItem(id=2, text="First Name"),
        ),
        target_language="fr",
        source_language="en",
    )

    response = await provider.translate_batch(request)
    assert response.translations_by_id[1] == "Nom de famille"
    assert response.translations_by_id[2] == "Prénom"
    assert response.usage is not None
    assert response.usage.provider_name == "gemini"
    assert response.usage.target_language == "fr"


@pytest.mark.asyncio
async def test_gemini_translation_same_language_short_circuit() -> None:
    mock_ai = MagicMock()
    provider = GeminiTranslationProvider(mock_ai)
    request = TranslationRequest(
        items=(TranslationItem(id=1, text="Hello"),),
        target_language="en",
        source_language="en",
    )

    response = await provider.translate_batch(request)
    assert response.translations_by_id[1] == "Hello"
    assert response.usage is not None
    assert response.usage.request_count == 0
    mock_ai.translate_output_batch.assert_not_called()
