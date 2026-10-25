"""Tests for GeminiAIProvider — HTTP calls are mocked; no real Gemini API is contacted."""

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
    AIProviderValidationError,
)
from app.ai.gemini_provider import GeminiAIProvider
from app.ai.schemas import (
    BatchTranslationItem,
    BatchTranslationRequest,
    ClarificationRequest,
    ExplanationRequest,
    ExtractionRequest,
    QuestionGenerationRequest,
    QuestionTranslationRequest,
    TranslationRequest,
)


def make_provider() -> GeminiAIProvider:
    return GeminiAIProvider(
        api_key="test-gemini-key",
        model="gemini-3.5-flash",
        timeout_seconds=5,
        max_retries=0,
    )


def _mock_gemini_response(
    body: dict[str, Any] | str, status_code: int = 200
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    text_content = json.dumps(body) if isinstance(body, dict) else body
    resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text_content}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ]
    }
    return resp


@pytest.mark.asyncio
async def test_extract_value_success() -> None:
    provider = make_provider()
    uncertainties: list[str] = []
    payload: dict[str, Any] = {
        "normalizedValue": {"amount": 2500, "currency": "EUR", "period": "month"},
        "outputValue": "2500 EUR per month",
        "requiresClarification": False,
        "uncertainties": uncertainties,
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(payload)

        result = await provider.extract_value(
            ExtractionRequest(
                field_id="income",
                field_type="money",
                answer="2500 euros monthly",
                user_language="en",
                source_language="en",
                output_language="en",
            )
        )

        assert result.requires_clarification is False
        assert result.normalized_value == {
            "amount": 2500,
            "currency": "EUR",
            "period": "month",
        }
        assert result.output_value == "2500 EUR per month"


@pytest.mark.asyncio
async def test_extract_value_with_markdown_fences() -> None:
    provider = make_provider()
    json_str = json.dumps(
        {
            "normalizedValue": "Alice",
            "outputValue": "Alice",
            "requiresClarification": False,
            "uncertainties": [],
        }
    )
    raw_markdown = f"```json\n{json_str}\n```"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(raw_markdown)

        result = await provider.extract_value(
            ExtractionRequest(
                field_id="first_name",
                field_type="string",
                answer="Alice",
                user_language="en",
                source_language="en",
                output_language="en",
            )
        )

        assert result.normalized_value == "Alice"
        assert result.output_value == "Alice"


@pytest.mark.asyncio
async def test_explain_field() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(
            {"explanation": "This field asks for your given name."}
        )

        res = await provider.explain_field(
            ExplanationRequest(
                field_id="first_name",
                field_type="string",
                field_label="First Name",
                user_language="en",
                source_language="en",
            )
        )
        assert res.explanation == "This field asks for your given name."


@pytest.mark.asyncio
async def test_clarify_answer() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(
            {"missingFields": ["currency"], "question": "Which currency is used?"}
        )

        res = await provider.clarify_answer(
            ClarificationRequest(
                field_id="salary",
                field_type="money",
                user_language="en",
                source_language="en",
                output_language="en",
                partial_normalized_value={"amount": 2000},
                uncertainties=["missing_currency"],
            )
        )
        assert "currency" in res.missing_fields
        assert res.question == "Which currency is used?"


@pytest.mark.asyncio
async def test_translate_output() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(
            {"translatedText": "Bonjour le monde"}
        )

        res = await provider.translate_output(
            TranslationRequest(
                text="Hello world",
                source_language="en",
                target_language="fr",
            )
        )
        assert res.translated_text == "Bonjour le monde"


@pytest.mark.asyncio
async def test_translate_output_batch() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(
            {
                "translations": [
                    {"id": 1, "translatedText": "Nom de famille"},
                    {"id": 2, "translatedText": "Prénom"},
                ]
            }
        )

        res = await provider.translate_output_batch(
            BatchTranslationRequest(
                items=[
                    BatchTranslationItem(id=1, text="Last Name"),
                    BatchTranslationItem(id=2, text="First Name"),
                ],
                sourceLanguage="en",
                targetLanguage="fr",
            )
        )
        assert res.translations_by_id[1] == "Nom de famille"
        assert res.translations_by_id[2] == "Prénom"


@pytest.mark.asyncio
async def test_translate_question() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(
            {"text": "Quel est votre nom?", "helpText": None, "placeholder": None}
        )

        res = await provider.translate_question(
            QuestionTranslationRequest(
                question_key="personal.name",
                field_type="string",
                source_language="en",
                target_language="fr",
                text="What is your name?",
            )
        )
        assert res.text == "Quel est votre nom?"


@pytest.mark.asyncio
async def test_generate_question() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(
            {
                "text": "Enter your email address",
                "helpText": "We will not spam you",
                "placeholder": "user@example.com",
            }
        )

        res = await provider.generate_question(
            QuestionGenerationRequest(
                question_key="contact.email",
                field_type="email",
                purpose="contact",
                required=True,
                target_language="en",
            )
        )
        assert res.text == "Enter your email address"
        assert res.placeholder == "user@example.com"


@pytest.mark.asyncio
async def test_health_check_success() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        resp = MagicMock()
        resp.status_code = 200
        mock_get.return_value = resp

        assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_health_check_failure() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        resp = MagicMock()
        resp.status_code = 404
        mock_get.return_value = resp

        assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_timeout_raises_ai_provider_timeout_error() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(AIProviderTimeoutError):
            await provider.explain_field(
                ExplanationRequest(
                    field_id="first_name",
                    field_type="string",
                    field_label="First Name",
                    user_language="en",
                    source_language="en",
                )
            )


@pytest.mark.asyncio
async def test_auth_error_raises_ai_provider_unavailable() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        resp = MagicMock()
        resp.status_code = 401
        mock_post.return_value = resp

        with pytest.raises(
            AIProviderUnavailableError, match="Gemini authentication failed"
        ):
            await provider.explain_field(
                ExplanationRequest(
                    field_id="first_name",
                    field_type="string",
                    field_label="First Name",
                    user_language="en",
                    source_language="en",
                )
            )


@pytest.mark.asyncio
async def test_malformed_json_raises() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(
            "This is completely unparseable gibberish"
        )

        with pytest.raises(AIProviderMalformedResponseError):
            await provider.explain_field(
                ExplanationRequest(
                    field_id="first_name",
                    field_type="string",
                    field_label="First Name",
                    user_language="en",
                    source_language="en",
                )
            )


@pytest.mark.asyncio
async def test_validation_error_raises() -> None:
    provider = make_provider()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Returns JSON but missing the required explanation key
        mock_post.return_value = _mock_gemini_response({"wrong_key": "some value"})

        with pytest.raises(AIProviderValidationError):
            await provider.explain_field(
                ExplanationRequest(
                    field_id="first_name",
                    field_type="string",
                    field_label="First Name",
                    user_language="en",
                    source_language="en",
                )
            )


@pytest.mark.asyncio
async def test_injected_client_and_aclose() -> None:
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    provider = GeminiAIProvider(
        api_key="test-key",
        client=mock_client,
    )
    assert provider._client is mock_client
    await provider.aclose()
    # If client was injected, provider does not close it (caller owns it)
    mock_client.aclose.assert_not_called()

    # Owned client is closed
    owned_provider = GeminiAIProvider(api_key="test-key")
    with patch.object(
        owned_provider._client, "aclose", new_callable=AsyncMock
    ) as mock_owned_close:
        await owned_provider.aclose()
        mock_owned_close.assert_called_once()


@pytest.mark.asyncio
async def test_api_key_sent_via_header_and_never_in_url() -> None:
    secret_key = "AIzaSy-SUPER-SECRET-DO-NOT-LEAK"
    provider = GeminiAIProvider(
        api_key=secret_key,
        model="gemini-3.5-flash",
        timeout_seconds=5,
        max_retries=0,
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = _mock_gemini_response(
            {
                "normalizedValue": "Berlin",
                "outputValue": "Berlin",
                "requiresClarification": False,
                "uncertainties": [],
            }
        )
        await provider.extract_value(
            ExtractionRequest(
                field_id="city",
                field_type="string",
                answer="Berlin",
                user_language="en",
                source_language="de",
                output_language="de",
            )
        )
        called_url = mock_post.call_args.args[0]
        called_headers = mock_post.call_args.kwargs["headers"]
        called_json = mock_post.call_args.kwargs["json"]
        assert secret_key not in called_url
        assert "key=" not in called_url
        assert called_headers["x-goog-api-key"] == secret_key
        assert "systemInstruction" in called_json
        assert "untrusted data" in called_json["systemInstruction"]["parts"][0]["text"]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        mock_get.return_value = ok_resp

        assert await provider.health_check() is True
        health_url = mock_get.call_args.args[0]
        health_headers = mock_get.call_args.kwargs["headers"]
        assert secret_key not in health_url
        assert "key=" not in health_url
        assert health_headers["x-goog-api-key"] == secret_key
