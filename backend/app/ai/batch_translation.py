"""Batched, cached, deduplicated text translation.

Replaces the one-AI-call-per-text pattern for the case where a whole set of
short texts is known up front — the dynamically detected field labels and
choice options a document produces (`app/field_detection/question_bridge.py`).

Measured on the German rental contract (24 fields, 4 choice options, one
target language): 28 sequential Ollama calls, ~41 s total, which exceeded the
frontend proxy's request ceiling and surfaced to the user as a processing
error while the backend was still working. Batching the same work into
bounded chunks takes one or two calls.

The ordering of the four cost-avoidance steps matters, cheapest first:

1. **Deduplicate.** The same source text appearing on five fields is
   translated once, not five times.
2. **Process cache.** A bounded LRU keyed on (source, target, text) — a
   second document sharing labels with the first pays nothing.
3. **Approved catalog translations.** A reusable question already approved
   in the target language is authoritative; per `docs/claude/domain-rules.md`
   the AI must not be called when one exists, and an AI guess must never
   displace approved human text.
4. **The provider, in bounded batches.** Only whatever is still unresolved.

Failure is always per item, never per document: a missing or invalid batch
entry falls back to a single-text call for just that text, and if that also
fails the source text is used unchanged. A document is never blocked, and a
field never silently receives another field's translation.

No text, label, or option value is ever logged here — only counts.
"""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from app.ai.errors import AIProviderError
from app.ai.mock_provider import AIProvider
from app.ai.schemas import BatchTranslationItem, BatchTranslationRequest
from app.ai.text_translation import translate_text

logger = logging.getLogger(__name__)

# Small local models degrade on very long instructions, so the work is split
# into chunks rather than sent as one 30-item request. Bounded by config.
_MIN_BATCH_SIZE = 1

# Bounded so a long-lived process cannot grow without limit. Entries are
# short label strings; a few thousand costs very little and spans many
# documents. Eviction is least-recently-used.
_CACHE_MAX_ENTRIES = 4096


@dataclass
class TranslationStats:
    """Per-run accounting, safe to log and to assert on in tests.

    Mutated from concurrently running chunks, which needs no lock: asyncio
    runs them on one thread and `+= 1` on a plain int never yields.
    """

    texts_requested: int = 0
    unique_texts: int = 0
    cache_hits: int = 0
    catalog_hits: int = 0
    provider_calls: int = 0
    batch_items_sent: int = 0
    fallback_single_calls: int = 0
    unresolved: int = 0

    @property
    def ollama_call_count(self) -> int:
        """Every call actually made to the AI provider, batched or single."""
        return self.provider_calls + self.fallback_single_calls


@dataclass
class _Cache:
    """Process-local LRU. Deliberately not a database table: translations of
    detected labels are a performance convenience, not a record of user data,
    and persisting them is not this phase's concern."""

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


def _chunk(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    step = max(size, _MIN_BATCH_SIZE)
    for start in range(0, len(items), step):
        yield items[start : start + step]


async def translate_texts(
    ai_provider: AIProvider,
    texts: Iterable[str],
    source_language: str,
    target_language: str,
    batch_size: int,
    concurrency: int = 1,
    stats: TranslationStats | None = None,
    approved_lookup: dict[str, str] | None = None,
) -> dict[str, str]:
    """Translates every distinct text in `texts` into `target_language`.

    Returns a `{source_text: translated_text}` map that always contains an
    entry for every input text, so callers need no None handling. When the
    languages match, or on total provider failure, that entry is the source
    text itself.

    `approved_lookup` is an optional `{source_text: approved_translation}`
    map the caller has already resolved from the question catalog; those
    texts never reach the provider.
    """
    stats = stats if stats is not None else TranslationStats()

    # Order-preserving dedup: identical text is translated exactly once, and
    # the batch we send is deterministic (which keeps tests meaningful).
    unique: list[str] = list(dict.fromkeys(t for t in texts if t))
    stats.texts_requested += len(list(unique))
    stats.unique_texts += len(unique)

    if source_language == target_language:
        return {text: text for text in unique}

    resolved: dict[str, str] = {}
    pending: list[str] = []
    for text in unique:
        approved = (approved_lookup or {}).get(text)
        if approved:
            resolved[text] = approved
            stats.catalog_hits += 1
            continue
        cached = _cache.get(source_language, target_language, text)
        if cached is not None:
            resolved[text] = cached
            stats.cache_hits += 1
            continue
        pending.append(text)

    # Chunks are independent, so they run concurrently — but strictly bounded.
    # Batching alone cut the reference document from 28 calls to 3; it barely
    # moved wall-clock time, because three sequential ~15 s generations still
    # add up to more than the frontend should wait. A small semaphore overlaps
    # them without flooding a single local Ollama instance (which queues
    # beyond its own parallelism and would just trade latency for timeouts).
    chunks = list(_chunk(pending, batch_size))
    semaphore = asyncio.Semaphore(max(concurrency, 1))

    async def run(chunk: Sequence[str]) -> dict[str, str]:
        async with semaphore:
            return await _translate_chunk(
                ai_provider, chunk, source_language, target_language, stats
            )

    for chunk_result in await asyncio.gather(*(run(chunk) for chunk in chunks)):
        resolved.update(chunk_result)

    return {text: resolved.get(text, text) for text in unique}


async def _translate_chunk(
    ai_provider: AIProvider,
    chunk: Sequence[str],
    source_language: str,
    target_language: str,
    stats: TranslationStats,
) -> dict[str, str]:
    """One provider call for up to `batch_size` texts, with per-item recovery.

    Ids are positions within this chunk only, and the mapping back to source
    text goes through that id — never through the order of the response — so
    a reordered or partial response cannot mislabel a field.
    """
    by_id = dict(enumerate(chunk))
    translations: dict[int, str] = {}

    try:
        stats.provider_calls += 1
        stats.batch_items_sent += len(chunk)
        result = await ai_provider.translate_output_batch(
            BatchTranslationRequest(
                items=[
                    BatchTranslationItem(id=index, text=text)
                    for index, text in by_id.items()
                ],
                sourceLanguage=source_language,
                targetLanguage=target_language,
            )
        )
        translations = dict(result.translations_by_id)
    except AIProviderError as exc:
        # The whole batch failed. Every item is recovered individually below
        # rather than losing the chunk.
        logger.warning(
            "Batch translation failed, falling back per item: "
            "target_language=%s items=%d error=%s",
            target_language,
            len(chunk),
            type(exc).__name__,
        )

    resolved: dict[str, str] = {}
    missing_ids: list[int] = []
    for index, text in by_id.items():
        candidate = translations.get(index)
        if candidate and candidate.strip():
            resolved[text] = candidate.strip()
            _cache.put(source_language, target_language, text, resolved[text])
        else:
            missing_ids.append(index)

    if missing_ids:
        logger.info(
            "Batch translation incomplete: target_language=%s missing=%d of %d; "
            "recovering those items individually",
            target_language,
            len(missing_ids),
            len(chunk),
        )

    # Per-item fallback for exactly what the batch did not deliver. Bounded by
    # the chunk size, so a hostile or broken provider cannot cause an
    # unbounded fan-out of calls.
    for index in missing_ids:
        text = by_id[index]
        stats.fallback_single_calls += 1
        single = await translate_text(
            ai_provider, text, source_language, target_language
        )
        if single.succeeded and single.translated_text:
            # An identical result is a legitimate translation (a German label
            # into German, "IBAN", a proper noun) — only an actual provider
            # failure counts as unresolved.
            resolved[text] = single.translated_text
            _cache.put(source_language, target_language, text, resolved[text])
        else:
            # translate_text already fell back to the source text; don't cache
            # that as if it were a translation, so a later run retries.
            resolved[text] = text
            stats.unresolved += 1

    return resolved
