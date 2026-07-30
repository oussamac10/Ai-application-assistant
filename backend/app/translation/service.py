"""The translation pipeline: what gets translated, by whom, and in what order.

This is Phase 14's `app/ai/batch_translation.py` pipeline, re-pointed at the
`TranslationProvider` abstraction. The cost-avoidance ordering is unchanged and
is still the whole point — every step below the first exists to *not* call a
provider:

1. **Protected text** (`protected.py`). An IBAN, email address, ISO date or
   internal token is never sent anywhere. Deterministic, per `domain-rules.md`.
2. **Deduplicate.** The same label on five fields is translated once.
3. **Approved catalog translations.** Approved human text is authoritative and
   the provider must not be called when it exists.
4. **Persisted (pending) catalog translations.** Text already translated once
   and stored is reused rather than paid for again.
5. **Process cache.** A bounded LRU keyed on (source, target, text).
6. **The primary provider**, for whatever is still unresolved — in one call.
7. **The fallback provider**, for only the ids the primary did not return.
8. **Source text**, for anything still missing.

Steps 7 and 8 are what make this safe to run in the request path: a provider
outage degrades a document to untranslated labels, never to a failure. And
recovery is always per item, so one bad element cannot cost a document its
other 23 questions.

Nothing here logs text, labels, option values or credentials — counts,
durations and language codes only.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.translation.base import (
    TranslationItem,
    TranslationProvider,
    TranslationRequest,
    TranslationResponse,
)
from app.translation.errors import TranslationProviderError
from app.translation.protected import partition_protected

logger = logging.getLogger(__name__)

# Bounded so a long-lived process cannot grow without limit. Entries are short
# label strings; a few thousand costs very little and spans many documents.
_CACHE_MAX_ENTRIES = 4096


# Why the fallback provider was invoked. Recorded so a slow or degraded run
# can be explained from a log line without reproducing it.
FALLBACK_REASONS = (
    "timeout",
    "authentication_error",
    "rate_limit",
    "transport_error",
    "invalid_response",
    "endpoint_not_found",
    "not_configured",
    "partial_response",
    "missing_item",
    "empty_translation",
    "unsupported_language",
)

_ERROR_CODE_TO_REASON = {
    "translation_timeout": "timeout",
    "translation_authentication_failed": "authentication_error",
    "translation_rate_limited": "rate_limit",
    "translation_failed": "transport_error",
    "translation_invalid_response": "invalid_response",
    "translation_endpoint_not_found": "endpoint_not_found",
    "translation_not_configured": "not_configured",
}


@dataclass
class TranslationStats:
    """Per-run accounting.

    Primary and fallback are measured **separately**. Reporting one
    `provider_latency` made a 42.9 s run look like Azure being slow when Azure
    had in fact failed in 0.2 s and the local model had done all the work; the
    log said `provider=azure` throughout. Anything that cannot be attributed to
    one provider does not belong in this dataclass.

    Request counters count **actual outbound requests**. Selecting a provider,
    or a provider short-circuiting a no-op, is not a request — counting it as
    one reported `provider_calls=1, characters=0, latency=0.00s`, which is not
    a thing that can happen.
    """

    unique_texts: int = 0
    protected_skipped: int = 0
    catalog_hits: int = 0
    persisted_hits: int = 0
    cache_hits: int = 0

    primary_provider: str = ""
    primary_request_count: int = 0
    primary_retry_count: int = 0
    primary_duration_seconds: float = 0.0
    primary_status_class: str = "none"

    fallback_provider: str = ""
    fallback_request_count: int = 0
    fallback_duration_seconds: float = 0.0
    fallback_reason: str = ""

    translated_character_count: int = 0
    unresolved: int = 0
    detected_source_languages: tuple[str, ...] = ()
    detection_confidence: float | None = None

    @property
    def total_request_count(self) -> int:
        """Every outbound request, both providers, retries included."""
        return self.primary_request_count + self.fallback_request_count

    @property
    def translation_total_duration(self) -> float:
        return self.primary_duration_seconds + self.fallback_duration_seconds

    @property
    def fallback_used(self) -> bool:
        return self.fallback_request_count > 0


@dataclass
class _Cache:
    """Process-local LRU. Deliberately not a database table: translations of
    detected labels are a performance convenience, not a record of user data."""

    entries: OrderedDict[tuple[str, str, str], str] = field(default_factory=OrderedDict)

    def get(self, source: str, target: str, text: str) -> str | None:
        key = (source, target, text)
        value = self.entries.get(key)
        if value is not None:
            self.entries.move_to_end(key)
        return value

    def put(self, source: str, target: str, text: str, translated: str) -> None:
        key = (source, target, text)
        self.entries[key] = translated
        self.entries.move_to_end(key)
        while len(self.entries) > _CACHE_MAX_ENTRIES:
            self.entries.popitem(last=False)

    def clear(self) -> None:
        self.entries.clear()


_cache = _Cache()


def clear_translation_cache() -> None:
    """Test seam — production never needs to drop the cache."""
    _cache.clear()


async def translate_texts(
    texts: Iterable[str],
    target_language: str,
    provider: TranslationProvider,
    fallback_provider: TranslationProvider | None = None,
    source_language: str | None = None,
    assumed_source_language: str = "en",
    stats: TranslationStats | None = None,
    approved_lookup: dict[str, str] | None = None,
    persisted_lookup: dict[str, str] | None = None,
) -> dict[str, str]:
    """Translates every distinct text into `target_language`.

    Returns a `{source_text: translated_text}` map containing an entry for
    every input text, so callers need no None handling. When the languages
    already match, when the text is protected, or on total provider failure,
    that entry is the source text itself.

    `source_language=None` asks the provider to detect it — the reason a German
    document no longer takes a pointless `en -> de` round trip.
    """
    stats = stats if stats is not None else TranslationStats()
    stats.primary_provider = getattr(provider, "provider_name", "unknown")

    # Order-preserving dedup keeps the request deterministic, which keeps the
    # tests and the logged counts meaningful.
    unique: list[str] = list(dict.fromkeys(t for t in texts if t))
    stats.unique_texts += len(unique)

    # An explicit source language equal to the target means there is nothing
    # to do. With detection enabled (source_language=None) we cannot know that
    # in advance, so the provider decides — Azure returns the text unchanged
    # when it detects the target language, at no extra cost.
    if source_language is not None and source_language == target_language:
        return {text: text for text in unique}

    translatable, protected = partition_protected(unique)
    stats.protected_skipped += len(protected)
    if protected:
        logger.info(
            "Translation skipped protected text: target_language=%s count=%d "
            "reasons=%s",
            target_language,
            len(protected),
            ",".join(sorted(set(protected.values()))),
        )

    cache_key_language = source_language or assumed_source_language
    # Protected text resolves to itself, unchanged.
    resolved: dict[str, str] = {text: text for text in protected}

    pending: list[str] = []
    for text in translatable:
        approved = (approved_lookup or {}).get(text)
        if approved:
            resolved[text] = approved
            stats.catalog_hits += 1
            continue
        persisted = (persisted_lookup or {}).get(text)
        if persisted:
            resolved[text] = persisted
            stats.persisted_hits += 1
            continue
        cached = _cache.get(cache_key_language, target_language, text)
        if cached is not None:
            resolved[text] = cached
            stats.cache_hits += 1
            continue
        pending.append(text)

    if pending:
        resolved.update(
            await _translate_pending(
                pending,
                target_language,
                provider,
                fallback_provider,
                source_language,
                assumed_source_language,
                cache_key_language,
                stats,
            )
        )

    return {text: resolved.get(text, text) for text in unique}


async def _translate_pending(
    pending: list[str],
    target_language: str,
    provider: TranslationProvider,
    fallback_provider: TranslationProvider | None,
    source_language: str | None,
    assumed_source_language: str,
    cache_key_language: str,
    stats: TranslationStats,
) -> dict[str, str]:
    """Primary provider, then the fallback for **only what is still missing**,
    then source text.

    Ids are positions in `pending` and never leave this function, so no
    application identifier reaches a provider.
    """
    items = tuple(
        TranslationItem(id=index, text=text) for index, text in enumerate(pending)
    )
    by_id = {item.id: item.text for item in items}
    request = TranslationRequest(
        items=items,
        target_language=target_language,
        source_language=source_language,
        assumed_source_language=assumed_source_language,
    )

    translations: dict[int, str] = {}
    detected: list[str] = []
    stats.primary_provider = getattr(provider, "provider_name", "unknown")

    try:
        response = await provider.translate_batch(request)
        translations.update(response.translations_by_id)
        _record_primary(stats, response, detected)
    except TranslationProviderError as exc:
        # A provider that raised may still have sent requests (a retried
        # timeout sends two), so the counters come from the exception path's
        # own accounting rather than being assumed zero.
        stats.primary_request_count += getattr(exc, "request_count", 0) or 0
        stats.primary_retry_count += getattr(exc, "retry_count", 0) or 0
        stats.primary_duration_seconds += getattr(exc, "duration_seconds", 0.0) or 0.0
        stats.primary_status_class = getattr(exc, "status_class", "") or "error"
        stats.fallback_reason = _ERROR_CODE_TO_REASON.get(
            exc.error_code, "transport_error"
        )
        logger.warning(
            "Primary translation provider failed: provider=%s target_language=%s "
            "items=%d error_code=%s reason=%s",
            stats.primary_provider,
            target_language,
            len(items),
            exc.error_code,
            stats.fallback_reason,
        )

    missing = [item for item in items if item.id not in translations]

    if missing:
        # Distinguish "the call failed" from "the call worked but skipped some
        # items" — they need different operator responses.
        if not stats.fallback_reason:
            stats.fallback_reason = (
                "partial_response" if translations else "missing_item"
            )

    if missing and fallback_provider is not None:
        stats.fallback_provider = getattr(fallback_provider, "provider_name", "unknown")
        logger.info(
            "Falling back for %d of %d item(s): provider=%s target_language=%s "
            "reason=%s",
            len(missing),
            len(items),
            stats.fallback_provider,
            target_language,
            stats.fallback_reason,
        )
        try:
            fallback_response = await fallback_provider.translate_batch(
                TranslationRequest(
                    # Only the items the primary did not deliver. One bad
                    # element must never cost a whole batch a second full pass.
                    items=tuple(missing),
                    target_language=target_language,
                    source_language=source_language,
                    assumed_source_language=assumed_source_language,
                )
            )
            translations.update(fallback_response.translations_by_id)
            _record_fallback(stats, fallback_response, detected)
        except TranslationProviderError as exc:
            stats.fallback_request_count += getattr(exc, "request_count", 0) or 0
            stats.fallback_duration_seconds += (
                getattr(exc, "duration_seconds", 0.0) or 0.0
            )
            logger.warning(
                "Fallback translation provider also failed: target_language=%s "
                "error_code=%s; using source text",
                target_language,
                exc.error_code,
            )

    if detected:
        stats.detected_source_languages = tuple(detected)

    resolved: dict[str, str] = {}
    for item_id, text in by_id.items():
        candidate = translations.get(item_id)
        if candidate and candidate.strip():
            resolved[text] = candidate.strip()
            _cache.put(cache_key_language, target_language, text, resolved[text])
        else:
            # Untranslated, deliberately *not* cached — caching the source text
            # as if it were a translation would make the failure permanent.
            resolved[text] = text
            stats.unresolved += 1

    if stats.unresolved:
        logger.info(
            "Translation incomplete: target_language=%s untranslated=%d of %d",
            target_language,
            stats.unresolved,
            len(items),
        )
    return resolved


def _record_primary(
    stats: TranslationStats, response: TranslationResponse, detected: list[str]
) -> None:
    """Folds one primary response into the stats.

    Counters come from the provider's own usage, so a provider that
    short-circuited without contacting anything contributes zero requests —
    which is the whole point of separating "we chose this provider" from "we
    called it".
    """
    usage = response.usage
    if usage is None:
        return
    stats.primary_request_count += usage.request_count
    stats.primary_retry_count += usage.retry_count
    stats.primary_duration_seconds += usage.latency_seconds
    stats.translated_character_count += usage.translated_character_count
    if usage.status_class != "none":
        stats.primary_status_class = usage.status_class
    if usage.detection_confidence is not None:
        stats.detection_confidence = usage.detection_confidence
    # Only genuine detections. A provider echoing the language it was told to
    # assume must not be able to outvote one that actually looked.
    if usage.source_language_is_detected:
        detected.extend(usage.detected_source_languages)


def _record_fallback(
    stats: TranslationStats, response: TranslationResponse, detected: list[str]
) -> None:
    usage = response.usage
    if usage is None:
        return
    stats.fallback_request_count += usage.request_count
    stats.fallback_duration_seconds += usage.latency_seconds
    stats.translated_character_count += usage.translated_character_count
    if usage.source_language_is_detected:
        detected.extend(usage.detected_source_languages)


async def translate_one(
    text: str,
    target_language: str,
    provider: TranslationProvider,
    fallback_provider: TranslationProvider | None = None,
    source_language: str | None = None,
    assumed_source_language: str = "en",
) -> str:
    """Single-text convenience wrapper. Goes through the same pipeline, so a
    one-off translation still benefits from the cache and the fallbacks."""
    start = time.perf_counter()
    result = await translate_texts(
        [text],
        target_language,
        provider,
        fallback_provider,
        source_language,
        assumed_source_language,
    )
    logger.debug("translate_one took %.3fs", time.perf_counter() - start)
    return result.get(text, text)
