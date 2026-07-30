"""Tests for batched/cached/deduplicated translation.

The behaviour under test is a cost and latency contract, not just a mapping
one: a 24-field document previously issued 28 sequential Ollama calls and took
long enough (~41 s) that the frontend proxy abandoned the request and showed a
processing error for a document the backend went on to finish. So these tests
assert on call *counts* as much as on returned text, and on the property that
matters most for correctness — that a field can never receive another field's
translation.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.ai.batch_translation import (
    TranslationStats,
    clear_translation_cache,
    translate_texts,
)
from app.ai.errors import AIProviderUnavailableError
from app.ai.schemas import BatchTranslationResult, TranslationResult


@pytest.fixture(autouse=True)
def clean_cache() -> Any:
    clear_translation_cache()
    yield
    clear_translation_cache()


class _RecordingProvider:
    """Counts batch and single calls separately, and translates by prefixing
    the target language so a mis-mapping is visible in the assertion."""

    def __init__(self) -> None:
        self.batch_calls: list[list[str]] = []
        self.single_calls: list[str] = []

    async def translate_output_batch(self, request: Any) -> BatchTranslationResult:
        self.batch_calls.append([item.text for item in request.items])
        return BatchTranslationResult(
            translationsById={
                item.id: f"[{request.target_language}] {item.text}"
                for item in request.items
            }
        )

    async def translate_output(self, request: Any) -> TranslationResult:
        self.single_calls.append(request.text)
        return TranslationResult(
            translatedText=f"[{request.target_language}] {request.text}"
        )


class _PartialProvider(_RecordingProvider):
    """Returns every item except the ones whose position is in `drop`, which
    is what a small local model actually does under load — it silently omits
    entries rather than failing."""

    def __init__(self, drop: set[int]) -> None:
        super().__init__()
        self._drop = drop

    async def translate_output_batch(self, request: Any) -> BatchTranslationResult:
        self.batch_calls.append([item.text for item in request.items])
        return BatchTranslationResult(
            translationsById={
                item.id: f"[{request.target_language}] {item.text}"
                for item in request.items
                if item.id not in self._drop
            }
        )


class _ShuffledIdProvider(_RecordingProvider):
    """Returns the correct id->text pairs but in reverse insertion order. A
    caller that mapped results positionally would silently swap fields."""

    async def translate_output_batch(self, request: Any) -> BatchTranslationResult:
        self.batch_calls.append([item.text for item in request.items])
        pairs = [
            (item.id, f"[{request.target_language}] {item.text}")
            for item in request.items
        ]
        return BatchTranslationResult(translationsById=dict(reversed(pairs)))


class _FailingBatchProvider(_RecordingProvider):
    async def translate_output_batch(self, request: Any) -> BatchTranslationResult:
        self.batch_calls.append([item.text for item in request.items])
        raise AIProviderUnavailableError("Ollama is unreachable")


def _labels(count: int) -> list[str]:
    return [f"Label {index}" for index in range(count)]


@pytest.mark.asyncio
async def test_24_fields_do_not_create_one_call_per_field() -> None:
    """The reported regression, stated as a bound: 24 labels plus 4 option
    values must not cost 28 provider calls."""
    provider = _RecordingProvider()
    stats = TranslationStats()
    texts = _labels(24) + ["Kitchen", "Bathroom", "Cellar", "Balcony"]

    result = await translate_texts(
        provider, texts, "en", "de", batch_size=12, stats=stats
    )

    assert len(result) == 28
    assert stats.ollama_call_count == 3, (
        f"expected 3 batched calls for 28 texts at batch_size=12, "
        f"got {stats.ollama_call_count}"
    )
    assert provider.single_calls == []
    assert result["Label 0"] == "[de] Label 0"
    assert result["Kitchen"] == "[de] Kitchen"


@pytest.mark.asyncio
async def test_batch_size_bounds_each_request() -> None:
    """Chunking is what keeps a long instruction from degrading a small local
    model, so the chunk bound must actually hold."""
    provider = _RecordingProvider()
    await translate_texts(provider, _labels(25), "en", "de", batch_size=10)

    assert [len(batch) for batch in provider.batch_calls] == [10, 10, 5]


@pytest.mark.asyncio
async def test_repeated_text_is_translated_once_within_a_run() -> None:
    provider = _RecordingProvider()
    stats = TranslationStats()
    texts = ["Name", "Date", "Name", "Name", "Date"]

    result = await translate_texts(
        provider, texts, "en", "de", batch_size=12, stats=stats
    )

    assert provider.batch_calls == [["Name", "Date"]]
    assert stats.unique_texts == 2
    assert result == {"Name": "[de] Name", "Date": "[de] Date"}


@pytest.mark.asyncio
async def test_repeated_text_uses_cached_translation_across_runs() -> None:
    provider = _RecordingProvider()
    await translate_texts(provider, ["Name", "Date"], "en", "de", batch_size=12)

    stats = TranslationStats()
    result = await translate_texts(
        provider, ["Name", "Date"], "en", "de", batch_size=12, stats=stats
    )

    assert len(provider.batch_calls) == 1, "second run must not call the provider"
    assert stats.cache_hits == 2
    assert stats.ollama_call_count == 0
    assert result["Name"] == "[de] Name"


@pytest.mark.asyncio
async def test_cache_is_scoped_per_target_language() -> None:
    """A German translation must never be served for a French request."""
    provider = _RecordingProvider()
    await translate_texts(provider, ["Name"], "en", "de", batch_size=12)
    result = await translate_texts(provider, ["Name"], "en", "fr", batch_size=12)

    assert result["Name"] == "[fr] Name"
    assert len(provider.batch_calls) == 2


@pytest.mark.asyncio
async def test_translation_mapping_survives_reordered_response() -> None:
    """Ordering is carried by ids, not by response position — this is the test
    that would fail if results were zipped onto the request list."""
    provider = _ShuffledIdProvider()
    texts = ["First name", "Last name", "Date of birth", "IBAN"]

    result = await translate_texts(provider, texts, "en", "de", batch_size=12)

    assert result == {text: f"[de] {text}" for text in texts}


@pytest.mark.asyncio
async def test_partial_batch_falls_back_per_missing_item_only() -> None:
    provider = _PartialProvider(drop={1, 3})
    stats = TranslationStats()
    texts = ["A", "B", "C", "D"]

    result = await translate_texts(
        provider, texts, "en", "de", batch_size=12, stats=stats
    )

    assert result == {text: f"[de] {text}" for text in texts}
    # Only the two dropped items were re-requested individually.
    assert sorted(provider.single_calls) == ["B", "D"]
    assert stats.fallback_single_calls == 2


@pytest.mark.asyncio
async def test_failed_batch_recovers_every_item_individually() -> None:
    provider = _FailingBatchProvider()
    stats = TranslationStats()

    result = await translate_texts(
        provider, ["A", "B"], "en", "de", batch_size=12, stats=stats
    )

    assert result == {"A": "[de] A", "B": "[de] B"}
    assert stats.fallback_single_calls == 2


@pytest.mark.asyncio
async def test_total_failure_falls_back_to_source_text_never_blocks() -> None:
    """Both paths down. The document must still be usable, with untranslated
    labels, rather than failing."""

    class _DeadProvider(_FailingBatchProvider):
        async def translate_output(self, request: Any) -> TranslationResult:
            raise AIProviderUnavailableError("Ollama is unreachable")

    stats = TranslationStats()
    result = await translate_texts(
        _DeadProvider(), ["A", "B"], "en", "de", batch_size=12, stats=stats
    )

    assert result == {"A": "A", "B": "B"}
    assert stats.unresolved == 2


@pytest.mark.asyncio
async def test_untranslated_text_is_not_cached_as_a_translation() -> None:
    """A failure must not poison the cache — once the provider recovers, the
    next run has to actually translate."""

    class _DeadProvider(_FailingBatchProvider):
        async def translate_output(self, request: Any) -> TranslationResult:
            raise AIProviderUnavailableError("Ollama is unreachable")

    await translate_texts(_DeadProvider(), ["A"], "en", "de", batch_size=12)

    healthy = _RecordingProvider()
    result = await translate_texts(healthy, ["A"], "en", "de", batch_size=12)

    assert result["A"] == "[de] A"
    assert healthy.batch_calls == [["A"]]


@pytest.mark.asyncio
async def test_matching_languages_make_no_call_at_all() -> None:
    provider = _RecordingProvider()
    result = await translate_texts(provider, ["A", "B"], "de", "de", batch_size=12)

    assert result == {"A": "A", "B": "B"}
    assert provider.batch_calls == []


@pytest.mark.asyncio
async def test_approved_catalog_text_wins_and_skips_the_provider() -> None:
    """Domain rule: approved human text is authoritative and the AI must not
    be called when it exists."""
    provider = _RecordingProvider()
    stats = TranslationStats()

    result = await translate_texts(
        provider,
        ["First name", "IBAN"],
        "en",
        "de",
        batch_size=12,
        stats=stats,
        approved_lookup={"First name": "Vorname"},
    )

    assert result["First name"] == "Vorname"
    assert result["IBAN"] == "[de] IBAN"
    assert provider.batch_calls == [["IBAN"]], "approved text must not be re-translated"
    assert stats.catalog_hits == 1


# ---------------------------------------------------------------------------
# Bounded concurrency
# ---------------------------------------------------------------------------


class _ConcurrencyProbe(_RecordingProvider):
    """Records how many batch calls are in flight simultaneously."""

    def __init__(self) -> None:
        super().__init__()
        self.in_flight = 0
        self.peak_in_flight = 0

    async def translate_output_batch(self, request: Any) -> BatchTranslationResult:
        import asyncio

        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        self.batch_calls.append([item.text for item in request.items])
        try:
            await asyncio.sleep(0.02)
            return BatchTranslationResult(
                translationsById={
                    item.id: f"[{request.target_language}] {item.text}"
                    for item in request.items
                }
            )
        finally:
            self.in_flight -= 1


@pytest.mark.asyncio
async def test_chunks_run_concurrently_up_to_the_limit() -> None:
    provider = _ConcurrencyProbe()
    await translate_texts(
        provider, _labels(30), "en", "de", batch_size=10, concurrency=3
    )

    assert len(provider.batch_calls) == 3
    assert provider.peak_in_flight == 3


@pytest.mark.asyncio
async def test_concurrency_never_exceeds_the_configured_bound() -> None:
    """Unbounded fan-out at a single local Ollama instance trades latency for
    timeouts, so the bound has to actually hold."""
    provider = _ConcurrencyProbe()
    await translate_texts(
        provider, _labels(100), "en", "de", batch_size=10, concurrency=2
    )

    assert len(provider.batch_calls) == 10
    assert provider.peak_in_flight <= 2


@pytest.mark.asyncio
async def test_concurrent_chunks_still_map_every_text_correctly() -> None:
    provider = _ConcurrencyProbe()
    texts = _labels(30)

    result = await translate_texts(
        provider, texts, "en", "de", batch_size=7, concurrency=3
    )

    assert result == {text: f"[de] {text}" for text in texts}


@pytest.mark.asyncio
async def test_default_is_sequential() -> None:
    provider = _ConcurrencyProbe()
    await translate_texts(provider, _labels(30), "en", "de", batch_size=10)

    assert provider.peak_in_flight == 1
