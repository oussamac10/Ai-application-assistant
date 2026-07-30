"""Provider metrics and fallback attribution.

Guards a specific, misleading log line observed in production:

    provider_calls=1 fallback_calls=1 characters=0 provider_latency=0.00s

which is not a thing that can happen — it counted *provider selection* as a
request. And a companion one:

    provider=azure provider_latency=42.62s

where Azure had in fact failed in 0.2s and the local model had spent the 42.6s.
Primary and fallback are therefore measured separately, and every counter comes
from a real outbound request.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest

from app.translation.base import (
    TranslationRequest,
    TranslationResponse,
    TranslationUsage,
)
from app.translation.errors import TranslationProviderError
from app.translation.service import (
    TranslationStats,
    clear_translation_cache,
    translate_texts,
)


@pytest.fixture(autouse=True)
def clean_cache() -> Generator[None, None, None]:
    clear_translation_cache()
    yield
    clear_translation_cache()


class _Provider:
    provider_name = "primary"

    def __init__(
        self,
        drop: set[int] | None = None,
        latency: float = 1.5,
        requests: int = 1,
        retries: int = 0,
    ) -> None:
        self._drop = drop or set()
        self._latency = latency
        self._requests = requests
        self._retries = retries
        self.calls = 0
        self.items_seen: list[str] = []

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        self.calls += 1
        self.items_seen.extend(item.text for item in request.items)
        return TranslationResponse(
            translations_by_id={
                item.id: f"[{request.target_language}] {item.text}"
                for item in request.items
                if item.id not in self._drop
            },
            usage=TranslationUsage(
                provider_name=self.provider_name,
                target_language=request.target_language,
                request_count=self._requests,
                retry_count=self._retries,
                status_class="2xx",
                latency_seconds=self._latency,
                translated_character_count=sum(len(i.text) for i in request.items),
                detected_source_languages=("de",) * len(request.items),
                source_language_is_detected=True,
            ),
        )

    async def health_check(self) -> bool:
        return True


class _Fallback(_Provider):
    provider_name = "fallback"


class _Failing:
    provider_name = "failing"

    def __init__(self, code: str = "translation_timeout", cost: float = 30.0) -> None:
        self._code = code
        self._cost = cost
        self.calls = 0

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        self.calls += 1
        raise TranslationProviderError(
            "down",
            self._code,
            request_count=2,
            retry_count=1,
            duration_seconds=self._cost,
            status_class="timeout",
        )

    async def health_check(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Counters reflect real requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_run_counts_one_primary_request_and_no_fallback() -> None:
    stats = TranslationStats()
    await translate_texts(
        ["Name", "Datum"], "fr", _Provider(), _Fallback(), stats=stats
    )

    assert stats.primary_request_count == 1
    assert stats.fallback_request_count == 0
    assert stats.fallback_reason == ""
    assert stats.primary_provider == "primary"


@pytest.mark.asyncio
async def test_same_language_no_op_makes_zero_outbound_calls() -> None:
    provider = _Provider()
    stats = TranslationStats()
    result = await translate_texts(
        ["Name"], "de", provider, source_language="de", stats=stats
    )

    assert provider.calls == 0
    assert stats.total_request_count == 0
    assert result == {"Name": "Name"}


@pytest.mark.asyncio
async def test_protected_only_input_makes_zero_outbound_calls() -> None:
    """Zero translatable characters must mean zero requests."""
    provider = _Provider()
    stats = TranslationStats()
    await translate_texts(
        ["user@example.com", "DE89 3704 0044 0532 0130 00", "2026-07-30"],
        "fr",
        provider,
        stats=stats,
    )

    assert provider.calls == 0
    assert stats.total_request_count == 0
    assert stats.translated_character_count == 0


@pytest.mark.asyncio
async def test_cache_only_request_makes_zero_outbound_calls() -> None:
    provider = _Provider()
    await translate_texts(["Name"], "fr", provider)

    stats = TranslationStats()
    await translate_texts(["Name"], "fr", provider, stats=stats)

    assert stats.total_request_count == 0
    assert stats.cache_hits == 1


@pytest.mark.asyncio
async def test_catalog_only_request_makes_zero_outbound_calls() -> None:
    provider = _Provider()
    stats = TranslationStats()
    await translate_texts(
        ["First name"],
        "fr",
        provider,
        stats=stats,
        approved_lookup={"First name": "Prénom"},
    )

    assert provider.calls == 0
    assert stats.total_request_count == 0
    assert stats.catalog_hits == 1


@pytest.mark.asyncio
async def test_a_provider_that_short_circuits_reports_no_request() -> None:
    """Selecting a provider is not calling it — this is the exact
    `provider_calls=1 characters=0 latency=0.00s` case."""

    class _ShortCircuit(_Provider):
        async def translate_batch(
            self, request: TranslationRequest
        ) -> TranslationResponse:
            self.calls += 1
            return TranslationResponse(
                translations_by_id={i.id: i.text for i in request.items},
                usage=TranslationUsage(
                    provider_name="short",
                    target_language=request.target_language,
                    request_count=0,
                    status_class="none",
                ),
            )

    stats = TranslationStats()
    await translate_texts(["Name"], "fr", _ShortCircuit(), stats=stats)

    assert stats.primary_request_count == 0
    assert stats.total_request_count == 0


@pytest.mark.asyncio
async def test_retries_are_counted_separately_from_requests() -> None:
    stats = TranslationStats()
    await translate_texts(["Name"], "fr", _Provider(requests=2, retries=1), stats=stats)

    assert stats.primary_request_count == 2
    assert stats.primary_retry_count == 1


# ---------------------------------------------------------------------------
# Primary and fallback are attributed separately
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_primary_and_fallback_durations_are_reported_separately() -> None:
    """The reported bug: 42.6s attributed to `provider=azure` when Azure had
    failed quickly and the local model spent the time."""
    stats = TranslationStats()
    await translate_texts(
        ["Name"],
        "fr",
        _Failing(cost=0.2),
        _Fallback(latency=42.6),
        stats=stats,
    )

    assert stats.primary_duration_seconds == pytest.approx(0.2)
    assert stats.fallback_duration_seconds == pytest.approx(42.6)
    assert stats.translation_total_duration == pytest.approx(42.8)
    assert stats.primary_provider == "failing"
    assert stats.fallback_provider == "fallback"


@pytest.mark.asyncio
async def test_a_failed_primary_still_reports_the_requests_it_spent() -> None:
    stats = TranslationStats()
    await translate_texts(["Name"], "fr", _Failing(), _Fallback(), stats=stats)

    assert stats.primary_request_count == 2
    assert stats.primary_retry_count == 1
    assert stats.primary_status_class == "timeout"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,reason",
    [
        ("translation_timeout", "timeout"),
        ("translation_authentication_failed", "authentication_error"),
        ("translation_rate_limited", "rate_limit"),
        ("translation_failed", "transport_error"),
        ("translation_invalid_response", "invalid_response"),
        ("translation_endpoint_not_found", "endpoint_not_found"),
        ("translation_not_configured", "not_configured"),
    ],
)
async def test_fallback_reason_records_why(code: str, reason: str) -> None:
    stats = TranslationStats()
    await translate_texts(["Name"], "fr", _Failing(code), _Fallback(), stats=stats)

    assert stats.fallback_reason == reason


@pytest.mark.asyncio
async def test_partial_response_is_distinguished_from_a_failure() -> None:
    stats = TranslationStats()
    await translate_texts(
        ["a", "b", "c"], "fr", _Provider(drop={1}), _Fallback(), stats=stats
    )

    assert stats.fallback_reason == "partial_response"


@pytest.mark.asyncio
async def test_one_missing_item_sends_only_that_item_to_the_fallback() -> None:
    """Never resend the whole batch because one element failed."""
    fallback = _Fallback()
    await translate_texts(["a", "b", "c", "d"], "fr", _Provider(drop={2}), fallback)

    assert fallback.items_seen == ["c"]


@pytest.mark.asyncio
async def test_a_wholly_failed_primary_sends_every_item_to_the_fallback() -> None:
    """Distinct from the partial case: nothing came back, so everything is
    missing and everything must be recovered."""
    fallback = _Fallback()
    await translate_texts(["a", "b"], "fr", _Failing(), fallback)

    assert sorted(fallback.items_seen) == ["a", "b"]


@pytest.mark.asyncio
async def test_detected_language_survives_a_fallback() -> None:
    """The fallback's *assumed* language must not replace the primary's real
    detection — and with no detection at all, none is reported."""

    class _AssumingFallback(_Fallback):
        async def translate_batch(
            self, request: TranslationRequest
        ) -> TranslationResponse:
            self.calls += 1
            return TranslationResponse(
                translations_by_id={i.id: i.text for i in request.items},
                usage=TranslationUsage(
                    provider_name="assuming",
                    target_language=request.target_language,
                    request_count=1,
                    detected_source_languages=("en",),
                    source_language_is_detected=False,
                ),
            )

    stats = TranslationStats()
    await translate_texts(
        ["a", "b"], "fr", _Provider(drop={1}), _AssumingFallback(), stats=stats
    )

    assert "en" not in stats.detected_source_languages
    assert set(stats.detected_source_languages) == {"de"}
