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


def _mock_response(body: dict[str, Any], thinking: str | None = None) -> MagicMock:
    """Return a fake httpx.Response mimicking Ollama's /api/generate wrapper:
    the final answer as a JSON string under "response", optionally alongside
    a "thinking" (chain-of-thought) field that must never be read."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    payload = {"response": json.dumps(body), "done": True}
    if thinking is not None:
        payload["thinking"] = thinking
    resp.json.return_value = payload
    return resp


def _mock_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    fake_response = MagicMock()
    fake_response.status_code = status_code
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=MagicMock(), response=fake_response
    )


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
async def test_extract_value_success_with_thinking_field_ignored() -> None:
    """A reasoning model may return both `response` and `thinking` — the
    final result must come from `response` only, and `thinking` must never
    surface anywhere in the returned result."""
    provider = make_provider()
    expected = {
        "normalizedValue": {"fullName": "oussama"},
        "outputValue": "oussama",
        "requiresClarification": False,
        "uncertainties": [],
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_mock_response(
            expected, thinking="Okay, the user said 'oussama'. Let me think..."
        ),
    ):
        result = await provider.extract_value(
            ExtractionRequest(
                fieldType="person_name",
                answer="oussama",
                userLanguage="en",
                sourceLanguage="en",
                outputLanguage="en",
            )
        )

    assert result.normalized_value == expected["normalizedValue"]
    assert not hasattr(result, "thinking")
    assert "thinking" not in result.model_dump()
    # The raw dumped result must never contain the chain-of-thought text.
    assert "Let me think" not in str(result.model_dump())


@pytest.mark.asyncio
async def test_extract_value_empty_response_field_raises_after_repair_retry() -> None:
    """Reproduces the real failure: Ollama sets done=True with an empty
    `response` (the model's entire answer landed in `thinking` instead).
    Must raise a malformed-response error rather than crash unexpectedly,
    and must attempt exactly one repair retry before giving up."""
    provider = make_provider()

    empty_resp = MagicMock()
    empty_resp.status_code = 200
    empty_resp.raise_for_status = MagicMock()
    empty_resp.json.return_value = {
        "response": "",
        "thinking": '{"normalizedValue": {"fullName": "oussama"}}',
        "done": True,
        "done_reason": "stop",
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=empty_resp,
    ) as mock_post:
        with pytest.raises(AIProviderMalformedResponseError):
            await provider.extract_value(
                ExtractionRequest(
                    fieldType="person_name",
                    answer="oussama",
                    userLanguage="en",
                    sourceLanguage="en",
                    outputLanguage="en",
                )
            )

    # One initial attempt + exactly one repair retry, never more.
    assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_extract_value_malformed_json_recovers_on_repair_retry() -> None:
    """If the first response is malformed but the repair retry returns
    valid JSON, extraction must succeed using the repaired result."""
    provider = make_provider()
    expected = {
        "normalizedValue": "clean value",
        "outputValue": "clean value",
        "requiresClarification": False,
        "uncertainties": [],
    }

    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.raise_for_status = MagicMock()
    bad_resp.json.return_value = {"response": "not json at all", "done": True}

    good_resp = _mock_response(expected)

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=[bad_resp, good_resp],
    ) as mock_post:
        result = await provider.extract_value(
            ExtractionRequest(
                fieldType="string",
                answer="test",
                userLanguage="en",
                sourceLanguage="en",
                outputLanguage="en",
            )
        )

    assert result.normalized_value == "clean value"
    assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_extract_value_model_not_found_raises_unavailable() -> None:
    provider = make_provider()

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=_mock_http_status_error(404),
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


@pytest.mark.asyncio
async def test_call_ollama_disables_thinking_and_requests_json() -> None:
    """The payload sent to Ollama must always disable thinking mode and
    request JSON — this is the fix for the empty-response failure."""
    provider = make_provider()
    captured_payload: dict[str, Any] = {}

    async def _capture_post(self: Any, url: str, json: dict[str, Any]) -> MagicMock:
        captured_payload.update(json)
        return _mock_response(
            {
                "normalizedValue": "x",
                "outputValue": "x",
                "requiresClarification": False,
                "uncertainties": [],
            }
        )

    with patch("httpx.AsyncClient.post", new=_capture_post):
        await provider.extract_value(
            ExtractionRequest(
                fieldType="string",
                answer="hello",
                userLanguage="en",
                sourceLanguage="en",
                outputLanguage="en",
            )
        )

    assert captured_payload["format"] == "json"
    assert captured_payload["think"] is False
    assert captured_payload["stream"] is False


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
