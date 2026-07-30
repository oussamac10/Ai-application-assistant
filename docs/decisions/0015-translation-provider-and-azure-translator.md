# ADR 0015 — A `TranslationProvider` abstraction, and Azure Translator behind it

- Status: Accepted
- Date: 2026-07-30
- Phase: 15 (Azure Translator Integration)

## Context

`docs/claude/domain-rules.md` has listed `TranslationProvider` as a required provider family since
the beginning, but the codebase never had one: translation rode on `AIProvider.translate_output`
and, after Phase 14, `AIProvider.translate_output_batch`.

That conflated two genuinely different capabilities. Language *understanding* — value extraction,
clarification, question generation — is a language-model job. Plain text *translation* is not; a
dedicated service does it faster, more cheaply and far more predictably. Phase 14's measurements
made the cost concrete: on the reference German rental contract, `prepare-questions` took **43.8 s**,
of which **34.3 s** was local-model translation — and that was *after* batching cut the call count
from 28 to 4. The remaining time was simply the model generating text.

Two further problems were structural rather than slow:

1. **The source language was assumed, never checked.** Field detection performs no
   document-language detection, so every generated version recorded `en` regardless of content.
   A German contract's labels were therefore both mislabelled *and* sent on an `en -> de` round
   trip that mostly returned them unchanged. Worse, a German document viewed in an English
   interface was never translated at all: the interface language matched the assumption, so the
   pipeline concluded there was nothing to do and the user read German labels.
2. **Everything was translated eagerly**, including the output language, which nobody sees until
   review or export — minutes later.

## Decision

### `TranslationProvider`, with three implementations

`app/translation/base.py` defines a batch-first contract: `translate_batch` takes many texts for
one target language and returns a mapping keyed by the caller's own ids. `MockTranslationProvider`,
`OllamaTranslationProvider` and `AzureTranslatorProvider` implement it; `app/translation/factory.py`
selects them from `TRANSLATION_PROVIDER` / `TRANSLATION_FALLBACK_PROVIDER`. `AIProvider` keeps every
non-translation responsibility unchanged.

Ollama stays a first-class implementation, not a legacy path. A developer with no Azure account
and a deployment whose Azure resource is down both still get translated questions.

### Ids, never positions

Azure Translator answers **positionally** — `translations[i]` corresponds to `body[i]`. The adapter
converts position to caller id explicitly, and only after verifying the element count matches; a
short, long, or non-list response is rejected outright rather than partially trusted.

This is the one failure mode here that corrupts user-facing data rather than merely costing time.
Accepting 2 results for 3 inputs would shift every later translation onto the wrong field — a
landlord's label on a tenant's question. Rejecting the batch costs one fallback call; accepting it
silently produces a wrong form.

Per-element validation is separate and softer: an element with no translations, a blank string, a
wrong shape, or only some *other* language is treated as missing, so the caller recovers exactly
that item.

### Source-language detection, and what it changed

Requests omit `from`, so Azure detects the source language and reports it per element. The detected
language then becomes the **form version's** `source_language`, which fixes the modelling problem
above: the original text is stored under the language it is actually written in, and the interface
language gets a real translation instead of being assumed identical.

`OllamaTranslationProvider` cannot detect. It says so — it reports the assumed language rather than
guessing, and short-circuits when that assumption makes source and target equal. So the assumption
is confined to the provider that genuinely has it, instead of being baked into the caller.

### Eager interface language, deferred output language

Only the interface language is translated during preparation. Other supported languages get
source-text placeholder rows, because `FormService.publish_version` requires an option translation
for every supported language and a version that claims one it has no rows for cannot publish —
exactly how Phase 14's choice-field bug manifested. `app/translation/backfill.py` replaces the
placeholders when the summary (review) is first requested; it is idempotent and never overwrites a
real translation.

Nothing is lost by the placeholder: choice-option *values* — what is actually written into the
form — are never translated at all, and answers are translated separately at answer time.

### Deterministic protection for identifiers

`app/translation/protected.py` withholds text that is *entirely* an identifier: email addresses,
IBANs (matched with spaces removed, since forms print them grouped), BICs, ISO and numeric dates,
phone numbers, currency amounts, URLs, UUIDs and internal keys. Deterministic per `domain-rules.md`
— a mangled IBAN is far worse than an untranslated label.

The rule is deliberately conservative in one direction. "IBAN des Vermieters" and "Date of birth"
are ordinary labels and must still be translated; over-matching would silently leave real labels in
the wrong language, which is the bug this phase exists to remove. Two false positives were caught
by tests while writing it: a space-grouped IBAN initially escaped, and hyphenated German words
("E-Mail-Adresse") were misread as machine tokens.

Names are **not** pattern-matched — there is no reliable way to distinguish a personal name from a
common noun, and `domain-rules.md` forbids automatic transliteration. Protection for names comes
from the layer above: user-entered *values* never enter this pipeline at all.

### Failure is always per item, never per document

Primary provider → fallback provider for only the ids the primary missed → source text for anything
still missing. A translation outage degrades a document to untranslated labels; it never fails one.

## Consequences

Measured on the reference PDF, fresh upload, through the proxy, with
`FIELD_DETECTION_PROVIDER=azure` and `TRANSLATION_PROVIDER=ollama`:

| | Phase 14 | Phase 15 |
|---|---|---|
| `total_duration` | 43.80 s | **5.20 s** |
| `translation_duration` | 34.27 s | **0.04 s** |
| provider calls | 4 | **0** |
| generated questions | 24 | 24 |
| repeat request | 0.09 s, 0 calls | **0.05 s, 0 calls** |

Both targets are met (translation under 3 s, total under 15 s). The gain comes from deferring the
output language, not from Azure — see the limitation below.

Accepted trade-offs and known limitations:

- **The live Azure Translator path is unverified.** No `AZURE_TRANSLATOR_API_KEY` is provisioned,
  so every Azure test here is mocked and the benchmark above ran on Ollama. The mocked tests cover
  the wire contract thoroughly (positional mapping, partial and malformed responses, auth, rate
  limiting, timeout, retry, chunking, secret handling), but a live run is still required before
  claiming the provider works end to end.
- **With Ollama selected, a German document in an English interface is still not translated.** The
  local model cannot detect a source language, so it falls back to the assumption and correctly
  concludes there is nothing to do. Only Azure resolves this. The pipeline is ready; the credential
  is not.
- **Arabic field *detection* is weak** — the Arabic test form yielded 2 fields from 27 raw
  candidates, with three separate labels merged into one. That is a Phase 13/14 detection concern
  (the blank-run and section heuristics are tuned for LTR German/English layout), untouched by this
  phase. Arabic text itself round-trips without corruption, and RTL rendering is unchanged.
- The translation cache remains process-local and is dropped on restart.
- Backfill writes to a published version's translation rows. Publishing freezes a version's
  *structure* — fields, keys, types, option values — not the display text of a language it was
  published without, and backfill changes only the latter.
