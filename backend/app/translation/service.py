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
)
from app.translation.errors import TranslationProviderError
from app.translation.protected import partition_protected

logger = logging.getLogger(__name__)

# Bounded so a long-lived process cannot grow without limit. Entries are short
# label strings; a few thousand costs very little and spans many documents.
_CACHE_MAX_ENTRIES = 4096


@dataclass
class TranslationStats:
    """Per-run accounting. Safe to log, and precise enough to assert on — the
    performance claims in this phase's docs are these numbers."""

    unique_texts: int = 0
    protected_skipped: int = 0
    catalog_hits: int = 0
    persisted_hits: int = 0
    cache_hits: int = 0
    provider_calls: int = 0
    fallback_provider_calls: int = 0
    translated_character_count: int = 0
    provider_latency_seconds: float = 0.0
    unresolved: int = 0
    detected_source_languages: tuple[str, ...] = ()
    primary_provider: str = ""
    fallback_used: bool = False

    @property
    def total_provider_calls(self) -> int:
        return self.provider_calls + self.fallback_provider_calls


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
    """Primary provider, then fallback provider for what is still missing,
    then source text. Ids are positions in `pending` and never leave this
    function, so no application identifier reaches a provider."""
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

    try:
        stats.provider_calls += 1
        response = await provider.translate_batch(request)
        translations.update(response.translations_by_id)
        if response.usage:
            stats.translated_character_count += (
                response.usage.translated_character_count
            )
            stats.provider_latency_seconds += response.usage.latency_seconds
            detected.extend(response.usage.detected_source_languages)
    except TranslationProviderError as exc:
        logger.warning(
            "Primary translation provider failed: provider=%s target_language=%s "
            "items=%d error_code=%s",
            getattr(provider, "provider_name", "unknown"),
            target_language,
            len(items),
            exc.error_code,
        )

    missing = [item for item in items if item.id not in translations]

    if missing and fallback_provider is not None:
        stats.fallback_used = True
        logger.info(
            "Falling back to the secondary translation provider: provider=%s "
            "target_language=%s items=%d",
            getattr(fallback_provider, "provider_name", "unknown"),
            target_language,
            len(missing),
        )
        try:
            stats.fallback_provider_calls += 1
            fallback_response = await fallback_provider.translate_batch(
                TranslationRequest(
                    items=tuple(missing),
                    target_language=target_language,
                    source_language=source_language,
                    assumed_source_language=assumed_source_language,
                )
            )
            translations.update(fallback_response.translations_by_id)
            if fallback_response.usage:
                stats.translated_character_count += (
                    fallback_response.usage.translated_character_count
                )
                stats.provider_latency_seconds += (
                    fallback_response.usage.latency_seconds
                )
                detected.extend(fallback_response.usage.detected_source_languages)
        except TranslationProviderError as exc:
            logger.warning(
                "Fallback translation provider also failed: target_language=%s "
                "error_code=%s; using source text",
                target_language,
                exc.error_code,
            )

    if detected:
        stats.detected_source_languages = tuple(sorted(set(detected)))

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
