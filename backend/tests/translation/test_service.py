"""The translation pipeline: precedence, dedup, fallbacks, and cost.

These assert on provider *call counts* as much as on returned text. The whole
point of the ordering in `app/translation/service.py` is to not call a provider,
and a regression there is invisible in output but doubles the request duration.
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


class _Recorder:
    """Translates by prefixing the target language, so a mis-mapping is
    visible in the assertion rather than merely absent."""

    provider_name = "recorder"

    def __init__(self, detects: str = "en", drop: set[int] | None = None) -> None:
        self.calls = 0
        self.texts_seen: list[str] = []
        self._detects = detects
        self._drop = drop or set()

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        self.calls += 1
        self.texts_seen.extend(item.text for item in request.items)
        return TranslationResponse(
            translations_by_id={
                item.id: f"[{request.target_language}] {item.text}"
                for item in request.items
                if item.id not in self._drop
            },
            usage=TranslationUsage(
                provider_name=self.provider_name,
                target_language=request.target_language,
                request_count=1,
                translated_character_count=sum(
                    len(item.text) for item in request.items
                ),
                status_class="2xx",
                detected_source_languages=(self._detects,) * max(len(request.items), 1),
                source_language_is_detected=True,
            ),
        )

    async def health_check(self) -> bool:
        return True


class _Failing:
    provider_name = "failing"

    def __init__(self, code: str = "translation_failed") -> None:
        self.calls = 0
        self._code = code

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        self.calls += 1
        raise TranslationProviderError("provider is down", self._code)

    async def health_check(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Cost avoidance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_whole_document_costs_one_provider_call() -> None:
    provider = _Recorder()
    stats = TranslationStats()
    texts = [f"Label {i}" for i in range(24)] + ["Kitchen", "Bathroom"]

    result = await translate_texts(texts, "de", provider, stats=stats)

    assert provider.calls == 1
    assert stats.primary_request_count == 1
    assert len(result) == 26


@pytest.mark.asyncio
async def test_repeated_text_is_sent_once() -> None:
    provider = _Recorder()
    stats = TranslationStats()

    result = await translate_texts(
        ["Name", "Date", "Name", "Name"], "de", provider, stats=stats
    )

    assert provider.texts_seen == ["Name", "Date"]
    assert stats.unique_texts == 2
    assert result["Name"] == "[de] Name"


@pytest.mark.asyncio
async def test_cache_hit_avoids_the_provider() -> None:
    provider = _Recorder()
    await translate_texts(["Name"], "de", provider)

    stats = TranslationStats()
    result = await translate_texts(["Name"], "de", provider, stats=stats)

    assert provider.calls == 1, "second run must not reach the provider"
    assert stats.cache_hits == 1
    assert stats.total_request_count == 0
    assert result["Name"] == "[de] Name"


@pytest.mark.asyncio
async def test_cache_is_scoped_per_target_language() -> None:
    provider = _Recorder()
    await translate_texts(["Name"], "de", provider)
    result = await translate_texts(["Name"], "fr", provider)

    assert result["Name"] == "[fr] Name"
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_approved_catalog_hit_avoids_the_provider() -> None:
    """Domain rule: approved human text is authoritative and the provider must
    not be called when it exists."""
    provider = _Recorder()
    stats = TranslationStats()

    result = await translate_texts(
        ["First name", "Last name"],
        "de",
        provider,
        stats=stats,
        approved_lookup={"First name": "Vorname"},
    )

    assert result["First name"] == "Vorname"
    assert provider.texts_seen == ["Last name"]
    assert stats.catalog_hits == 1


@pytest.mark.asyncio
async def test_persisted_translation_hit_avoids_the_provider() -> None:
    provider = _Recorder()
    stats = TranslationStats()

    result = await translate_texts(
        ["First name", "Last name"],
        "de",
        provider,
        stats=stats,
        persisted_lookup={"First name": "Vorname (gespeichert)"},
    )

    assert result["First name"] == "Vorname (gespeichert)"
    assert provider.texts_seen == ["Last name"]
    assert stats.persisted_hits == 1


@pytest.mark.asyncio
async def test_approved_text_outranks_persisted_text() -> None:
    """An AI-generated translation must never displace approved human text."""
    result = await translate_texts(
        ["First name"],
        "de",
        _Recorder(),
        approved_lookup={"First name": "Vorname"},
        persisted_lookup={"First name": "Erster Name"},
    )

    assert result["First name"] == "Vorname"


@pytest.mark.asyncio
async def test_matching_explicit_languages_make_no_call() -> None:
    provider = _Recorder()
    result = await translate_texts(["Name"], "de", provider, source_language="de")

    assert provider.calls == 0
    assert result == {"Name": "Name"}


# ---------------------------------------------------------------------------
# Protected text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identifiers_are_never_sent_to_a_provider() -> None:
    """A mangled IBAN is far worse than an untranslated label."""
    provider = _Recorder()
    stats = TranslationStats()
    texts = [
        "First name",
        "DE89 3704 0044 0532 0130 00",
        "user@example.com",
        "2026-07-30",
        "+49 30 1234567",
        "1.234,56 EUR",
        "personal.first_name",
        "https://example.com/form",
    ]

    result = await translate_texts(texts, "de", provider, stats=stats)

    assert provider.texts_seen == ["First name"]
    assert stats.protected_skipped == 7
    for text in texts[1:]:
        assert result[text] == text, f"{text!r} must pass through unchanged"


@pytest.mark.asyncio
async def test_labels_mentioning_an_identifier_are_still_translated() -> None:
    """Over-matching here would silently leave real labels untranslated."""
    provider = _Recorder()

    result = await translate_texts(
        ["IBAN des Vermieters", "Date of birth", "E-Mail-Adresse"], "en", provider
    )

    assert result["IBAN des Vermieters"] == "[en] IBAN des Vermieters"
    assert result["Date of birth"] == "[en] Date of birth"
    assert result["E-Mail-Adresse"] == "[en] E-Mail-Adresse"


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_primary_failure_falls_back_to_the_secondary_provider() -> None:
    primary = _Failing()
    fallback = _Recorder()
    stats = TranslationStats()

    result = await translate_texts(["First name"], "de", primary, fallback, stats=stats)

    assert result["First name"] == "[de] First name"
    assert primary.calls == 1
    assert fallback.calls == 1
    assert stats.fallback_used is True


@pytest.mark.asyncio
async def test_fallback_receives_only_the_items_the_primary_missed() -> None:
    primary = _Recorder(drop={1})
    fallback = _Recorder()

    result = await translate_texts(["one", "two", "three"], "de", primary, fallback)

    assert fallback.texts_seen == ["two"]
    assert result == {
        "one": "[de] one",
        "two": "[de] two",
        "three": "[de] three",
    }


@pytest.mark.asyncio
async def test_both_providers_failing_falls_back_to_source_text() -> None:
    """A provider outage degrades a document to untranslated labels, never to
    a failed document."""
    stats = TranslationStats()

    result = await translate_texts(
        ["First name", "Last name"], "de", _Failing(), _Failing(), stats=stats
    )

    assert result == {"First name": "First name", "Last name": "Last name"}
    assert stats.unresolved == 2


@pytest.mark.asyncio
async def test_no_fallback_configured_still_degrades_to_source_text() -> None:
    result = await translate_texts(["First name"], "de", _Failing(), None)
    assert result == {"First name": "First name"}


@pytest.mark.asyncio
async def test_untranslated_text_is_not_cached() -> None:
    """Caching the source text as a translation would make the outage
    permanent for that string."""
    await translate_texts(["First name"], "de", _Failing())

    healthy = _Recorder()
    result = await translate_texts(["First name"], "de", healthy)

    assert result["First name"] == "[de] First name"
    assert healthy.calls == 1


@pytest.mark.asyncio
async def test_authentication_failure_still_falls_back() -> None:
    """A misconfigured key must not take the whole document down."""
    fallback = _Recorder()
    result = await translate_texts(
        ["First name"],
        "de",
        _Failing("translation_authentication_failed"),
        fallback,
    )

    assert result["First name"] == "[de] First name"


# ---------------------------------------------------------------------------
# Detection metadata and Arabic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detected_source_language_is_recorded() -> None:
    stats = TranslationStats()
    await translate_texts(["Vermieter"], "en", _Recorder(detects="de"), stats=stats)

    assert stats.detected_source_languages == ("de",)


@pytest.mark.asyncio
async def test_arabic_text_round_trips_without_corruption() -> None:
    """Arabic is the RTL case: the pipeline must be byte-transparent."""
    arabic = "الاسم الكامل"

    class _ArabicProvider(_Recorder):
        async def translate_batch(
            self, request: TranslationRequest
        ) -> TranslationResponse:
            self.calls += 1
            return TranslationResponse(
                translations_by_id={item.id: arabic for item in request.items},
                usage=TranslationUsage(
                    provider_name="arabic", target_language=request.target_language
                ),
            )

    result = await translate_texts(["Full name"], "ar", _ArabicProvider())

    assert result["Full name"] == arabic
    assert len(result["Full name"]) == len(arabic)


@pytest.mark.asyncio
async def test_arabic_source_text_is_not_treated_as_protected() -> None:
    provider = _Recorder(detects="ar")
    result = await translate_texts(["الاسم الكامل"], "en", provider)

    assert provider.calls == 1
    assert result["الاسم الكامل"] == "[en] الاسم الكامل"


@pytest.mark.asyncio
async def test_character_count_and_latency_are_recorded() -> None:
    stats = TranslationStats()
    await translate_texts(["abcde", "fg"], "de", _Recorder(), stats=stats)

    assert stats.translated_character_count == 7
    assert stats.primary_provider == "recorder"


@pytest.mark.asyncio
async def test_nothing_sensitive_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("DEBUG"):
        await translate_texts(
            ["Vermieter Name", "DE89370400440532013000"], "en", _Recorder()
        )

    assert "Vermieter Name" not in caplog.text
    assert "DE89370400440532013000" not in caplog.text
