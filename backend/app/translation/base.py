"""The `TranslationProvider` abstraction.

`docs/claude/domain-rules.md` has named `TranslationProvider` as a required
provider family since the beginning, but until Phase 15 translation rode on
`AIProvider`. That conflated two genuinely different capabilities: language
*understanding* (value extraction, clarification, question generation — a
language-model job) and plain text *translation* (a dedicated service does it
faster, more cheaply and far more predictably). This module separates them.
`AIProvider` keeps every non-translation responsibility unchanged.

The contract is deliberately **batch-first**: `translate_batch` takes many
texts for one target language and returns a mapping keyed by the caller's own
ids. Two consequences are load-bearing:

- One target language per request. Asking a provider for two languages at once
  is ambiguous for LLM-backed implementations and unsupported by Azure's API.
- **Ids, never positions.** Azure Translator answers positionally, so its
  adapter must convert position to id explicitly and verify the count. Passing
  order through end to end would mean a provider that drops or reorders one
  element silently moves one field's translation onto another field — the one
  failure mode here that corrupts user-facing data rather than merely costing
  time.

A provider returns only what it is confident about. Ids it could not translate
are simply absent; deciding what to do about them (fallback provider, then
source text) belongs to `app/translation/service.py`, not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TranslationItem:
    """One text to translate, carried with the id the caller maps results back
    by. The id is the caller's own index — never a field key, document id or
    any other application identifier, so nothing about the document leaks into
    a provider request beyond the text itself."""

    id: int
    text: str


@dataclass(frozen=True)
class TranslationRequest:
    """A batch of texts bound for exactly one target language.

    `source_language` is optional: `None` means "let the provider detect it".
    That matters for real documents — a German contract's labels are not
    English, and forcing an `en -> de` path both wastes a request and risks a
    nonsense result. Providers that cannot detect must fall back to
    `assumed_source_language`.
    """

    items: tuple[TranslationItem, ...]
    target_language: str
    source_language: str | None = None
    assumed_source_language: str = "en"


@dataclass(frozen=True)
class TranslationUsage:
    """What the call cost and how it behaved. Counts, timings and language
    codes only — never text, never credentials.

    `request_count` counts **actual outbound HTTP requests**, retries included.
    A provider that short-circuits without contacting anything reports 0, which
    is what makes "did we really call out?" answerable from a log line. Callers
    must derive their own counters from this rather than from "we selected a
    provider" — conflating the two reported `provider_calls=1` for a request
    that never left the process.
    """

    provider_name: str
    target_language: str
    request_count: int = 0
    retry_count: int = 0
    # Coarse outcome of the last HTTP exchange: "2xx", "4xx", "5xx",
    # "timeout", "transport", or "none" when nothing was sent. Coarse on
    # purpose — a precise status can carry information about the request.
    status_class: str = "none"
    translated_character_count: int = 0
    latency_seconds: float = 0.0
    # Languages the provider genuinely *detected*, one entry per item, with
    # duplicates preserved so the caller can apply a frequency policy to a
    # mixed-language document.
    detected_source_languages: tuple[str, ...] = ()
    # False when the provider cannot detect and is merely echoing the language
    # it was told to assume. Without this flag an assumption is
    # indistinguishable from a detection, and the Ollama fallback's assumed
    # "en" silently overrode Azure's real answer.
    source_language_is_detected: bool = False
    # Confidence the provider reported for its language detection, when it
    # reports one. Never invented: absent unless the provider documents it.
    detection_confidence: float | None = None
    request_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TranslationResponse:
    """Translations for the ids the provider could handle.

    A missing id is not an error here — it is information the caller needs in
    order to recover that item specifically.
    """

    translations_by_id: dict[int, str] = field(default_factory=dict)
    usage: TranslationUsage | None = None

    def missing_ids(self, requested: tuple[TranslationItem, ...]) -> tuple[int, ...]:
        return tuple(
            item.id for item in requested if item.id not in self.translations_by_id
        )


@runtime_checkable
class TranslationProvider(Protocol):
    """Every translation backend implements exactly this."""

    provider_name: str

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        """Translates every item into `request.target_language`.

        Must not raise for an individual untranslatable item — omit its id
        instead. Raise `TranslationProviderError` only when the call as a
        whole failed (transport, auth, rate limit, unusable response).
        """
        ...

    async def health_check(self) -> bool: ...
