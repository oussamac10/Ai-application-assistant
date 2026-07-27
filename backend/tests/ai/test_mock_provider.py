"""Tests for MockAIProvider — confirms names/emails/identifiers are never
semantically translated during answer extraction, and that the original
answer text is always preserved regardless of output_language."""

from __future__ import annotations

import pytest

from app.ai.mock_provider import MockAIProvider
from app.ai.schemas import ExtractionRequest


@pytest.mark.asyncio
async def test_person_name_is_not_translated_to_output_language() -> None:
    provider = MockAIProvider()
    result = await provider.extract_value(
        ExtractionRequest(
            fieldType="person_name",
            answer="Ahmed Benali",
            userLanguage="en",
            sourceLanguage="en",
            outputLanguage="de",
        )
    )

    assert result.normalized_value == {"fullName": "Ahmed Benali"}
    assert result.output_value == "Ahmed Benali"


@pytest.mark.asyncio
async def test_email_is_not_translated_to_output_language() -> None:
    provider = MockAIProvider()
    result = await provider.extract_value(
        ExtractionRequest(
            fieldType="email",
            answer="ahmed.benali@example.com",
            userLanguage="en",
            sourceLanguage="en",
            outputLanguage="ar",
        )
    )

    assert result.normalized_value == "ahmed.benali@example.com"
    assert result.output_value == "ahmed.benali@example.com"


@pytest.mark.asyncio
async def test_free_text_extraction_preserves_answer_when_output_language_differs() -> (
    None
):
    """Free-text answers may be translated to output_language only after
    preserving the original answer — the extraction result must never lose
    the original text, whatever normalization/translation is applied."""
    provider = MockAIProvider()
    original = "I need help with my housing application."
    result = await provider.extract_value(
        ExtractionRequest(
            fieldType="multiline_text",
            answer=original,
            userLanguage="en",
            sourceLanguage="en",
            outputLanguage="de",
        )
    )

    # The mock provider's default (no-op) extraction never discards the
    # original text — a real translation step must be built the same way.
    assert result.normalized_value == original
    assert result.output_value == original
