"""Azure Translator wire contract.

No test here contacts Azure: every call goes through a stubbed
`httpx.AsyncClient`. The properties pinned are the ones that would corrupt
user-facing data or leak credentials if they regressed — positional-to-id
mapping above all, since Azure answers by position and a silent off-by-one
would move one field's label onto another field.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import httpx
import pytest

from app.core.config import settings
from app.translation.base import TranslationItem, TranslationRequest
from app.translation.errors import TranslationProviderError
from app.translation.providers.azure import AzureTranslatorProvider

_KEY = "test-subscription-key"
_ENDPOINT = "https://api.cognitive.microsofttranslator.example"


@pytest.fixture(autouse=True)
def enable_azure() -> Generator[None, None, None]:
    original = (settings.AZURE_TRANSLATOR_ENABLED, settings.AZURE_TRANSLATOR_API_KEY)
    settings.AZURE_TRANSLATOR_ENABLED = True
    settings.AZURE_TRANSLATOR_API_KEY = _KEY
    yield
    settings.AZURE_TRANSLATOR_ENABLED, settings.AZURE_TRANSLATOR_API_KEY = original


class _StubClient:
    """Stands in for httpx.AsyncClient, recording what was sent."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    async def post(
        self,
        url: str,
        json: Any = None,
        headers: dict[str, str] | None = None,
        timeout: Any = None,
    ) -> httpx.Response:
        self.requests.append({"url": url, "body": json, "headers": headers or {}})
        nxt = (
            self._responses.pop(0) if self._responses else httpx.Response(200, json=[])
        )
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


def _response(
    payload: Any, status: int = 200, request_id: str = "req-1"
) -> httpx.Response:
    return httpx.Response(
        status,
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json", "x-requestid": request_id},
    )


def _provider(
    responses: list[Any], **kwargs: Any
) -> tuple[AzureTranslatorProvider, _StubClient]:
    client = _StubClient(responses)
    provider = AzureTranslatorProvider(
        endpoint=_ENDPOINT,
        api_key=_KEY,
        region="westeurope",
        client=client,  # type: ignore[arg-type]
        **kwargs,
    )
    return provider, client


def _request(
    *texts: str, target: str = "de", source: str | None = None
) -> TranslationRequest:
    return TranslationRequest(
        items=tuple(TranslationItem(id=i, text=t) for i, t in enumerate(texts)),
        target_language=target,
        source_language=source,
    )


def _payload(*translations: str, detected: str = "en") -> list[dict[str, Any]]:
    return [
        {
            "detectedLanguage": {"language": detected, "score": 0.99},
            "translations": [{"text": text, "to": "de"}],
        }
        for text in translations
    ]


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_translates_a_batch_in_one_request() -> None:
    provider, client = _provider([_response(_payload("Vorname", "Nachname", "IBAN"))])

    result = await provider.translate_batch(_request("First name", "Last name", "IBAN"))

    assert result.translations_by_id == {0: "Vorname", 1: "Nachname", 2: "IBAN"}
    assert len(client.requests) == 1, "the whole batch must go in one array request"
    assert client.requests[0]["body"] == [
        {"Text": "First name"},
        {"Text": "Last name"},
        {"Text": "IBAN"},
    ]


@pytest.mark.asyncio
async def test_source_language_is_omitted_so_azure_detects_it() -> None:
    provider, client = _provider([_response(_payload("Vorname", detected="de"))])

    result = await provider.translate_batch(_request("Vorname"))

    assert "from=" not in client.requests[0]["url"]
    assert result.usage is not None
    assert result.usage.detected_source_languages == ("de",)
    assert result.usage.detection_confidence == pytest.approx(0.99)


@pytest.mark.asyncio
async def test_explicit_source_language_is_sent() -> None:
    provider, client = _provider([_response(_payload("Vorname"))])

    await provider.translate_batch(_request("First name", source="en"))

    assert "from=en" in client.requests[0]["url"]


@pytest.mark.asyncio
async def test_empty_request_makes_no_call() -> None:
    provider, client = _provider([])

    result = await provider.translate_batch(
        TranslationRequest(items=(), target_language="de")
    )

    assert result.translations_by_id == {}
    assert client.requests == []


@pytest.mark.asyncio
async def test_batches_larger_than_the_limit_are_chunked() -> None:
    provider, client = _provider(
        [_response(_payload(*[f"t{i}" for i in range(2)])) for _ in range(3)],
        max_batch_size=2,
    )

    result = await provider.translate_batch(_request("a", "b", "c", "d"))

    # 4 items at a limit of 2 = 2 requests; ids stay correct across chunks.
    assert len(client.requests) == 2
    assert sorted(result.translations_by_id) == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# Positional mapping — the property that protects user-facing data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_positions_map_to_the_requested_ids_in_order() -> None:
    provider, _ = _provider([_response(_payload("eins", "zwei", "drei"))])

    result = await provider.translate_batch(_request("one", "two", "three"))

    assert result.translations_by_id == {0: "eins", 1: "zwei", 2: "drei"}


@pytest.mark.asyncio
async def test_short_response_is_rejected_rather_than_misaligned() -> None:
    """Accepting 2 results for 3 inputs would shift every later translation
    onto the wrong field — far worse than translating nothing."""
    provider, _ = _provider([_response(_payload("eins", "zwei"))])

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one", "two", "three"))

    assert excinfo.value.error_code == "translation_invalid_response"


@pytest.mark.asyncio
async def test_long_response_is_rejected() -> None:
    provider, _ = _provider([_response(_payload("eins", "zwei", "drei"))])

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one", "two"))

    assert excinfo.value.error_code == "translation_invalid_response"


@pytest.mark.asyncio
async def test_non_list_response_is_rejected() -> None:
    provider, _ = _provider([_response({"error": "nope"})])

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one"))

    assert excinfo.value.error_code == "translation_invalid_response"


@pytest.mark.asyncio
async def test_non_json_response_is_rejected() -> None:
    provider, _ = _provider([httpx.Response(200, content=b"<html>gateway</html>")])

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one"))

    assert excinfo.value.error_code == "translation_invalid_response"


# ---------------------------------------------------------------------------
# Partial and malformed elements — one bad item, not one bad document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_element_without_translations_is_omitted_not_fatal() -> None:
    payload = _payload("eins", "zwei")
    payload[1] = {"detectedLanguage": {"language": "en", "score": 1.0}}
    provider, _ = _provider([_response(payload)])

    result = await provider.translate_batch(_request("one", "two"))

    assert result.translations_by_id == {0: "eins"}
    assert result.missing_ids(_request("one", "two").items) == (1,)


@pytest.mark.asyncio
async def test_blank_translation_is_treated_as_missing() -> None:
    payload = _payload("eins", "   ")
    provider, _ = _provider([_response(payload)])

    result = await provider.translate_batch(_request("one", "two"))

    assert result.translations_by_id == {0: "eins"}


@pytest.mark.asyncio
async def test_element_of_the_wrong_shape_is_skipped() -> None:
    payload: list[Any] = _payload("eins")
    payload.append("not a dict")
    provider, _ = _provider([_response(payload)])

    result = await provider.translate_batch(_request("one", "two"))

    assert result.translations_by_id == {0: "eins"}


@pytest.mark.asyncio
async def test_translation_for_another_language_only_is_not_used() -> None:
    """An entry carrying only French when German was asked for must be
    treated as missing, never guessed at."""
    payload = [
        {"translations": [{"text": "bonjour", "to": "fr"}]},
        {"translations": [{"text": "zwei", "to": "de"}]},
    ]
    provider, _ = _provider([_response(payload)])

    result = await provider.translate_batch(_request("one", "two"))

    assert result.translations_by_id == {1: "zwei"}


@pytest.mark.asyncio
async def test_regional_target_matches_its_base_language() -> None:
    payload = [{"translations": [{"text": "Hallo", "to": "de-DE"}]}]
    provider, _ = _provider([_response(payload)])

    result = await provider.translate_batch(_request("Hello", target="de"))

    assert result.translations_by_id == {0: "Hallo"}


# ---------------------------------------------------------------------------
# Failure mapping and retries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authentication_failure_is_mapped_and_not_retried() -> None:
    provider, client = _provider(
        [_response({"error": {"code": 401000}}, status=401)] * 3
    )

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one"))

    assert excinfo.value.error_code == "translation_authentication_failed"
    assert len(client.requests) == 1, "bad credentials must not be retried"


@pytest.mark.asyncio
async def test_rate_limit_is_retried_once_then_raised() -> None:
    provider, client = _provider(
        [_response({}, status=429), _response({}, status=429)], max_retries=1
    )

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one"))

    assert excinfo.value.error_code == "translation_rate_limited"
    assert len(client.requests) == 2, "exactly one retry"


@pytest.mark.asyncio
async def test_rate_limit_then_success_recovers() -> None:
    provider, client = _provider(
        [_response({}, status=429), _response(_payload("eins"))], max_retries=1
    )

    result = await provider.translate_batch(_request("one"))

    assert result.translations_by_id == {0: "eins"}
    assert len(client.requests) == 2
    assert result.usage is not None
    # Usage counts the retry honestly.
    assert result.usage.request_count == 2


@pytest.mark.asyncio
async def test_timeout_is_mapped_to_a_timeout_code() -> None:
    provider, _ = _provider(
        [httpx.TimeoutException("timed out"), httpx.TimeoutException("timed out")]
    )

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one"))

    assert excinfo.value.error_code == "translation_timeout"


@pytest.mark.asyncio
async def test_transport_error_is_mapped() -> None:
    provider, _ = _provider([httpx.ConnectError("refused")] * 2)

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one"))

    assert excinfo.value.error_code == "translation_failed"


@pytest.mark.asyncio
async def test_server_error_is_retried() -> None:
    provider, client = _provider(
        [_response({}, status=503), _response(_payload("eins"))], max_retries=1
    )

    result = await provider.translate_batch(_request("one"))

    assert result.translations_by_id == {0: "eins"}
    assert len(client.requests) == 2


@pytest.mark.asyncio
async def test_retries_can_be_disabled() -> None:
    provider, client = _provider([_response({}, status=503)] * 2, max_retries=0)

    with pytest.raises(TranslationProviderError):
        await provider.translate_batch(_request("one"))

    assert len(client.requests) == 1


@pytest.mark.asyncio
async def test_unconfigured_provider_reports_it_rather_than_calling() -> None:
    settings.AZURE_TRANSLATOR_ENABLED = False
    provider, client = _provider([_response(_payload("eins"))])

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("one"))

    assert excinfo.value.error_code == "translation_not_configured"
    assert client.requests == []


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_key_travels_only_in_the_header_never_the_url() -> None:
    provider, client = _provider([_response(_payload("eins"))])

    await provider.translate_batch(_request("one"))

    sent = client.requests[0]
    assert sent["headers"]["Ocp-Apim-Subscription-Key"] == _KEY
    assert sent["headers"]["Ocp-Apim-Subscription-Region"] == "westeurope"
    assert _KEY not in sent["url"]


@pytest.mark.asyncio
async def test_no_secret_or_body_text_reaches_a_raised_error() -> None:
    """An error message can end up in a log; a response body can echo the
    submitted document text back."""
    provider, _ = _provider(
        [
            _response(
                {"error": {"message": "key abc123 rejected for 'Mietvertrag'"}},
                status=401,
            )
        ]
    )

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("Mietvertrag"))

    rendered = str(excinfo.value)
    assert _KEY not in rendered
    assert "abc123" not in rendered
    assert "Mietvertrag" not in rendered


@pytest.mark.asyncio
async def test_nothing_sensitive_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider, _ = _provider([_response(_payload("Vorname"))])

    with caplog.at_level("DEBUG"):
        await provider.translate_batch(_request("First name"))

    logged = caplog.text
    assert _KEY not in logged
    assert "First name" not in logged, "source text must never be logged"
    assert "Vorname" not in logged, "translated text must never be logged"
    # Counts and languages are fine, and are what makes the logs useful.
    assert "target_language=de" in logged


# ---------------------------------------------------------------------------
# Source-language detection and `from` omission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_german_result_reports_de() -> None:
    provider, _ = _provider([_response(_payload("Bailleur", detected="de"))])

    result = await provider.translate_batch(_request("Vermieter", target="fr"))

    assert result.usage is not None
    assert result.usage.detected_source_languages == ("de",)
    assert result.usage.source_language_is_detected is True


@pytest.mark.asyncio
async def test_arabic_result_reports_ar() -> None:
    provider, _ = _provider([_response(_payload("Family name", detected="ar"))])

    result = await provider.translate_batch(_request("اسم العائلة", target="en"))

    assert result.usage is not None
    assert result.usage.detected_source_languages == ("ar",)


@pytest.mark.asyncio
async def test_detection_is_reported_per_item_not_deduplicated() -> None:
    """A mixed batch must keep its per-item answers so the caller can apply a
    frequency policy; collapsing to a set would lose the majority."""
    payload = (
        _payload("a", detected="de")
        + _payload("b", detected="en")
        + _payload("c", detected="de")
    )
    provider, _ = _provider([_response(payload)])

    result = await provider.translate_batch(_request("x", "y", "z"))

    assert result.usage is not None
    assert result.usage.detected_source_languages == ("de", "en", "de")


@pytest.mark.asyncio
async def test_from_is_omitted_when_no_source_language_is_known() -> None:
    """`und` must never be sent as `from=en`."""
    provider, client = _provider([_response(_payload("x"))])

    await provider.translate_batch(_request("Vermieter", source=None))

    assert "from=" not in client.requests[0]["url"]


@pytest.mark.asyncio
async def test_from_is_sent_only_for_a_trusted_source_language() -> None:
    provider, client = _provider([_response(_payload("x"))])

    await provider.translate_batch(_request("Vermieter", source="de"))

    assert "from=de" in client.requests[0]["url"]


@pytest.mark.asyncio
async def test_malformed_detection_metadata_does_not_break_the_batch() -> None:
    payload = [
        {"detectedLanguage": "not-a-dict", "translations": [{"text": "x", "to": "de"}]},
        {
            "detectedLanguage": {"score": "high"},
            "translations": [{"text": "y", "to": "de"}],
        },
    ]
    provider, _ = _provider([_response(payload)])

    result = await provider.translate_batch(_request("a", "b"))

    # Translations still land; only the unusable metadata is ignored.
    assert result.translations_by_id == {0: "x", 1: "y"}
    assert result.usage is not None
    assert result.usage.detected_source_languages == ()


@pytest.mark.asyncio
async def test_an_unsupported_detected_language_is_carried_not_rejected() -> None:
    """An unfamiliar code must not crash a document."""
    provider, _ = _provider([_response(_payload("x", detected="tlh"))])

    result = await provider.translate_batch(_request("a"))

    assert result.usage is not None
    assert result.usage.detected_source_languages == ("tlh",)


# ---------------------------------------------------------------------------
# Endpoint form
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_subdomain_endpoint_uses_the_translator_path() -> None:
    """A `*.cognitiveservices.azure.com` resource serves Text Translation at
    /translator/text/v3.0/translate and answers 404 for a bare /translate —
    which is exactly how a misconfigured endpoint silently fell back to the
    local model while the logs still said `provider=azure`."""
    client = _StubClient([_response(_payload("x"))])
    provider = AzureTranslatorProvider(
        endpoint="https://my-resource.cognitiveservices.azure.com",
        api_key=_KEY,
        region="germanywestcentral",
        client=client,  # type: ignore[arg-type]
    )

    await provider.translate_batch(_request("a"))

    assert "/translator/text/v3.0/translate" in client.requests[0]["url"]


@pytest.mark.asyncio
async def test_global_endpoint_uses_the_plain_path() -> None:
    client = _StubClient([_response(_payload("x"))])
    provider = AzureTranslatorProvider(
        endpoint="https://api.cognitive.microsofttranslator.com",
        api_key=_KEY,
        client=client,  # type: ignore[arg-type]
    )

    await provider.translate_batch(_request("a"))

    url = client.requests[0]["url"]
    assert "/translate?" in url
    assert "/translator/text" not in url


@pytest.mark.asyncio
async def test_404_is_reported_as_a_configuration_problem_and_not_retried() -> None:
    provider, client = _provider(
        [_response({"error": {"code": "404"}}, status=404)] * 3
    )

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("a"))

    assert excinfo.value.error_code == "translation_endpoint_not_found"
    assert len(client.requests) == 1, "a wrong endpoint will not fix itself on retry"


@pytest.mark.asyncio
async def test_a_failed_call_reports_what_it_cost() -> None:
    provider, _ = _provider([_response({}, status=503), _response({}, status=503)])

    with pytest.raises(TranslationProviderError) as excinfo:
        await provider.translate_batch(_request("a"))

    assert excinfo.value.request_count == 2
    assert excinfo.value.retry_count == 1
    assert excinfo.value.duration_seconds >= 0.0
