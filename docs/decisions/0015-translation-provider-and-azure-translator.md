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


---

# Addendum — automatic document-language detection, honest metrics, RTL grouping

- Status: Accepted
- Date: 2026-07-30

Live testing with `TRANSLATION_PROVIDER=azure` exposed four defects. Three were
real bugs; one was a configuration problem that the third bug had been hiding.

## What the logs said, and what was actually happening

```
provider=azure  provider_latency=42.62s  detected_source=en  fallback_calls=1
```

Every part of that is misleading. Azure was failing in ~0.15 s with an HTTP 4xx
(the configured endpoint is a *Document Intelligence* resource, whose key is not
valid for Translator); Ollama was spending the 42.6 s; and `detected_source=en`
was Ollama's **assumed** language being recorded as if it were a detection.

## Decisions

### 1. Language detection is its own capability

`app/language/` adds `DocumentLanguageDetector` with a deterministic,
dependency-free local implementation. It runs once per document immediately
after text extraction or OCR, is persisted on `source_documents`, and is reused
on every later request.

Relying on Azure Translator's `detectedLanguage` alone could never have worked:
it only arrives *with* a translation, so a document needing no translation has
no answer, and a provider failure silently replaces a real detection with an
assumption. Detection therefore outranks provider metadata in the precedence
chain.

Detection is script-first (Arabic, Hebrew, Greek, Cyrillic and CJK are decided
by Unicode block — a document in Arabic script is Arabic regardless of word
statistics), then function-word frequency for Latin scripts, with diacritics
breaking ties. Confidence is a measured ratio, never an invented number.

**`und` is a real answer.** A form with eight words in it has no determinable
language, and `domain-rules.md` forbids inventing information. Guessing "en" is
what caused the original bug. `und` never becomes `from=en` on an Azure
request — the parameter is omitted entirely so Azure detects instead.

The only place `und` is replaced by a concrete code is where the data model
structurally requires one: a `FormVersion.source_language`. The honest `und`
stays recorded on the source document.

### 2. Assumption and detection are different things

`TranslationUsage.source_language_is_detected` distinguishes them. Ollama
cannot detect a language, so it reports `False` and its assumed language can no
longer outvote Azure's real one. This single flag is what fixes
`detected_source=en` for a German document.

### 3. Primary and fallback are measured separately

`provider_latency` conflated two providers under whichever name was selected.
Now: `primary_provider`, `primary_request_count`, `primary_retry_count`,
`primary_duration`, `primary_status_class`, `fallback_provider`,
`fallback_request_count`, `fallback_duration`, `fallback_reason`. Counters come
from each provider's own usage and count **actual outbound requests**, so a
provider that short-circuits a no-op reports zero — the previously impossible
`provider_calls=1, characters=0, latency=0.00s` can no longer be produced.

A failed call still reports what it cost: `TranslationProviderError` carries its
own request count, retry count and duration, so a retried timeout is attributed
to the provider that spent the budget.

### 4. Two independent causes of "27 candidates → 2 questions"

Only one was geometric, and it was not the important one.

**`normalize_field_name` erased non-Latin scripts.** `[^a-z0-9]+` reduced
*every* Arabic label to the literal `"field"`, so deduplication collapsed the
whole document. Fixed by trying the original ASCII slug first — keeping every
existing German/English key byte-identical, including awkward ones like
`Straße` → `stra_e` — and falling back to a Unicode-aware slug only when ASCII
yields nothing.

**Azure merged rows into one key-value pair.** A key spanning several lines had
paired "family name", "place of birth" and "postal code" into a single question.
A field label occupies one line, so a multi-line key is split into one candidate
per line, at slightly reduced confidence and without the value pairing (the
pairing Azure made was wrong; only the labels survive).

**Geometry is now direction-aware** for `ar`/`he`/`fa`/`ur`: tokens are ordered
by *reading position* rather than ascending x, and a value region is associated
with the label on its **right**. Ordering by x reversed Arabic word order — the
form's title came back as `سكني دعم طلب نموذج` instead of
`نموذج طلب دعم سكني`. Only token *order* is direction-aware; the strings are
never touched, so Arabic characters survive byte for byte.

### 5. Tests never reach a live provider

`tests/conftest.py` pins the provider settings. `Settings` reads the
developer's real `.env`, so `TRANSLATION_PROVIDER=azure` had made the suite
issue live Azure calls — it hung for minutes on timeouts instead of finishing in
about one, and violated the rule that automated tests never call a live or paid
provider.

## Consequences

Measured live, fresh uploads:

| | Before | After |
|---|---|---|
| German: `source_language` | `en` | **`de`** (confidence 0.89, 0.04 s) |
| German: questions | 24 | 24 |
| Arabic: `source_language` | `en` | **`ar`** (confidence 0.99) |
| Arabic: raw → questions | 27 → **2** | 29 → **29** |
| Arabic: merged labels | 1 (three fields in one) | **0** |
| Repeat request | 0.09 s, 0 calls | 0.09 s, 0 calls |

The German request still takes ~51 s, and the logs now say exactly why:
`primary_duration=0.14s primary_status_class=4xx fallback_reason=authentication_error`
`fallback_duration=46.37s`. That is a credential problem, not a code one — see
the limitation below.

Known limitations:

- **Azure Translator is still not reachable.** `AZURE_TRANSLATOR_ENDPOINT`
  points at a Document Intelligence resource and its key is not valid for
  Translator: `/translate` → 404, `/translator/text/v3.0/translate` → 401, and
  the global endpoint → 401. A separate **Translator** resource is required.
  Until then every request pays the Ollama fallback, which is the whole of the
  remaining latency.
- The local detector covers Latin-script European languages and major
  non-Latin scripts. It is not a general-purpose language identifier.
- RTL geometry improves ordering and label association, but Azure's own
  key-value grouping for RTL documents is still the dominant signal for Arabic
  forms; the local text passes contribute little there.
