"""Tests for OllamaAIProvider — HTTP calls are mocked; no real Ollama is contacted."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.ai.errors import (
    AIProviderMalformedResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.ai.ollama_provider import OllamaAIProvider
from app.ai.schemas import (
    ClarificationRequest,
    ExplanationRequest,
    ExtractionRequest,
    TranslationRequest,
)


def make_provider() -> OllamaAIProvider:
    return OllamaAIProvider(
        base_url="http://localhost:11434",
        model="test-model",
        timeout_seconds=5,
        max_retries=0,
    )


def _mock_response(body: dict[str, Any]) -> MagicMock:
    """Return a fake httpx.Response that yields JSON with a 'response' key."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"response": json.dumps(body)}
    return resp


# ---------------------------------------------------------------------------
# extract_value
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_value_success() -> None:
    provider = make_provider()
    expected = {
        "normalizedValue": {"amount": 1800, "currency": "EUR", "period": "monthly"},
        "outputValue": "1 800 EUR mensuel",
        "requiresClarification": False,
        "uncertainties": [],
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_mock_response(expected),
    ):
        result = await provider.extract_value(
            ExtractionRequest(
                fieldType="money",
                answer="راتبي 1800 يورو شهريًا",
                userLanguage="ar",
                sourceLanguage="fr",
                outputLanguage="fr",
            )
        )

    assert result.normalized_value == expected["normalizedValue"]
    assert result.requires_clarification is False


@pytest.mark.asyncio
async def test_extract_value_malformed_json() -> None:
    provider = make_provider()

    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"response": "this is not JSON {"}

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=resp,
    ):
        with pytest.raises(AIProviderMalformedResponseError):
            await provider.extract_value(
                ExtractionRequest(
                    fieldType="string",
                    answer="test",
                    userLanguage="en",
                    sourceLanguage="en",
                    outputLanguage="en",
                )
            )


@pytest.mark.asyncio
async def test_extract_value_timeout_after_retries() -> None:
    provider = OllamaAIProvider(
        base_url="http://localhost:11434",
        model="test-model",
        timeout_seconds=1,
        max_retries=1,
    )

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ReadTimeout("timeout", request=MagicMock()),
    ):
        with pytest.raises(AIProviderTimeoutError):
            await provider.extract_value(
                ExtractionRequest(
                    fieldType="string",
                    answer="hello",
                    userLanguage="en",
                    sourceLanguage="en",
                    outputLanguage="en",
                )
            )


@pytest.mark.asyncio
async def test_extract_value_connect_error() -> None:
    provider = make_provider()

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("refused"),
    ):
        with pytest.raises(AIProviderUnavailableError):
            await provider.extract_value(
                ExtractionRequest(
                    fieldType="string",
                    answer="hello",
                    userLanguage="en",
                    sourceLanguage="en",
                    outputLanguage="en",
                )
            )


# ---------------------------------------------------------------------------
# explain_field
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explain_field_success() -> None:
    provider = make_provider()
    expected_body = {"explanation": "Please enter your monthly income."}

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_mock_response(expected_body),
    ):
        result = await provider.explain_field(
            ExplanationRequest(
                fieldType="money",
                fieldLabel="Monthly income",
                userLanguage="en",
                sourceLanguage="en",
            )
        )

    assert result.explanation == "Please enter your monthly income."


# ---------------------------------------------------------------------------
# clarify_answer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clarify_answer_success() -> None:
    provider = make_provider()
    expected_body = {
        "missingFields": ["currency"],
        "question": "Which currency are you referring to?",
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_mock_response(expected_body),
    ):
        result = await provider.clarify_answer(
            ClarificationRequest(
                fieldType="money",
                uncertainties=["currency"],
                userLanguage="en",
                sourceLanguage="en",
                outputLanguage="en",
            )
        )

    assert "currency" in result.missing_fields
    assert "currency" in result.question.lower()


# ---------------------------------------------------------------------------
# translate_output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_translate_output_success() -> None:
    provider = make_provider()
    expected_body = {"translatedText": "1 800 EUR par mois"}

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_mock_response(expected_body),
    ):
        result = await provider.translate_output(
            TranslationRequest(
                text="1 800 EUR monthly",
                sourceLanguage="en",
                targetLanguage="fr",
            )
        )

    assert result.translated_text == "1 800 EUR par mois"


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_model_available() -> None:
    provider = make_provider()
    tags_response = MagicMock()
    tags_response.status_code = 200
    tags_response.json.return_value = {
        "models": [{"name": "test-model:latest"}, {"name": "other-model"}]
    }

    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        return_value=tags_response,
    ):
        result = await provider.health_check()

    assert result is True


@pytest.mark.asyncio
async def test_health_check_model_not_available() -> None:
    provider = make_provider()
    tags_response = MagicMock()
    tags_response.status_code = 200
    tags_response.json.return_value = {"models": [{"name": "other-model"}]}

    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        return_value=tags_response,
    ):
        result = await provider.health_check()

    assert result is False


@pytest.mark.asyncio
async def test_health_check_connect_failure() -> None:
    provider = make_provider()
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("refused"),
    ):
        result = await provider.health_check()

    assert result is False
