# Phase 15 — Azure Translator Integration

Extracts the `TranslationProvider` abstraction that `docs/claude/domain-rules.md` has always
required, and implements Azure Translator behind it. Full rationale in
[ADR 0015](../decisions/0015-translation-provider-and-azure-translator.md).

## What changed

```
TranslationProvider                       app/translation/base.py
├── MockTranslationProvider               app/translation/providers/mock.py
├── OllamaTranslationProvider             app/translation/providers/ollama.py
└── AzureTranslatorProvider               app/translation/providers/azure.py

app/translation/factory.py     provider selection (mock | ollama | azure)
app/translation/service.py     the pipeline: protect -> dedup -> catalog -> cache -> provider
app/translation/protected.py   deterministic identifier detection
app/translation/backfill.py    fills deferred languages on demand
app/translation/errors.py      safe internal error codes
```

`AIProvider` keeps every non-translation responsibility unchanged.

## Resolution order

Each step exists to *avoid* a provider call:

1. Protected text (identifiers) — never sent anywhere
2. Deduplicate
3. Approved catalog translations
4. Persisted (pending) catalog translations
5. Process cache
6. Primary provider — one array request for everything still unresolved
7. Fallback provider — only the ids the primary did not return
8. Source text — anything still missing

## Configuration

```bash
TRANSLATION_PROVIDER=azure          # mock | ollama | azure
TRANSLATION_FALLBACK_PROVIDER=ollama  # or "none"; must differ from the primary

AZURE_TRANSLATOR_ENABLED=true
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
AZURE_TRANSLATOR_API_KEY=<key>        # git-ignored root .env only
AZURE_TRANSLATOR_REGION=<region>      # required for a regional resource
AZURE_TRANSLATOR_API_VERSION=3.0
AZURE_TRANSLATOR_TIMEOUT_SECONDS=30
AZURE_TRANSLATOR_MAX_RETRIES=1
AZURE_TRANSLATOR_MAX_BATCH_SIZE=50
```

Validated (fail fast) only when Azure is the selected or fallback provider, so a developer with no
Azure account can still boot.

## Source-language detection

Requests omit `from`, so Azure detects the source language and reports it per element. The detected
language becomes the generated form version's `source_language`, so the original label text is
stored under the language it is actually written in.

This fixes a real defect, not just a cost: field detection performs no language detection, so every
version previously claimed `en`. A German document viewed in an English interface was therefore
never translated — the interface language matched the assumption, so the pipeline concluded there
was nothing to do.

`OllamaTranslationProvider` cannot detect and says so, reporting the assumed language rather than
guessing, and short-circuiting when that assumption makes source and target equal.

## Eager vs deferred languages

Only the **interface** language is translated during preparation. Other supported languages get
source-text placeholder rows — `publish_version` requires a row for every supported language — and
`backfill.py` replaces them when the summary is first requested. It is idempotent and never
overwrites a real translation.

Choice-option **values** are never translated in any path; only their display labels are.

## Diagnostics

Counts, durations and language codes only — never text, labels, option values or credentials:

```
Question generation result: document=... questions=24 skipped=0 version=published
    supported_output_languages=de,en source_language=en eager_language=en
    deferred_languages=de translation_duration=0.04s provider=ollama unique_texts=28
    protected_skipped=0 catalog_hits=0 persisted_hits=0 cache_hits=0 provider_calls=1
    fallback_calls=0 characters=0 provider_latency=0.00s detected_source=en untranslated=0
prepare-questions timing: ... detection_duration=4.80s question_resolution_duration=0.39s
    total_duration=5.20s status=ready questions=24
```

## Benchmark

German rental contract, fresh upload, through the Next proxy,
`FIELD_DETECTION_PROVIDER=azure` + `TRANSLATION_PROVIDER=ollama`:

| | Phase 14 | Phase 15 | Target |
|---|---|---|---|
| `total_duration` | 43.80 s | **5.20 s** | < 15 s |
| `translation_duration` | 34.27 s | **0.04 s** | < 3 s |
| provider calls | 4 | **0** | — |
| generated questions | 24 | 24 | 24 |
| repeat request | 0.09 s, 0 calls | **0.05 s, 0 calls** | 0 calls |

First question still `vermieter_name` / "Vermieter – Name".

## Automatic document-language detection

`app/language/` detects what language the uploaded form is written in, once per
document, right after text extraction or OCR and before anything language-sensitive.

```
DocumentLanguageDetector                app/language/detector.py
├── LocalDocumentLanguageDetector       deterministic, dependency-free
└── MockDocumentLanguageDetector        tests

app/language/sampling.py                filtered, bounded text sample (max 5000 chars)
app/language/service.py                 detect / persist / reuse + precedence
```

Detection is script-first (Arabic, Hebrew, Greek, Cyrillic, CJK decided by Unicode
block), then function-word frequency for Latin scripts, with diacritics breaking ties.
The sample excludes identifiers using the same deterministic rules as
`app/translation/protected.py`, so IBANs and dates cannot bias the answer.

Persisted on `source_documents`: `detected_source_language`,
`language_detection_confidence`, `language_detection_provider`,
`language_detection_version`, `language_detected_at` (migration `e1975a7403eb`).
A repeat request reuses it and calls no detector.

### Precedence

1. explicit trusted form-definition language
2. persisted document-language result
3. the dedicated detector
4. Azure Translator's `detectedLanguage` metadata
5. `und`

The detector outranks Azure metadata because Azure only reports a language as a
*side effect* of translating — so it is absent exactly when a document needs no
translation, and a provider failure would otherwise replace a real answer with an
assumption.

### `und`

`und` (ISO 639-2 "undetermined") is a real answer, not a failure: a form with fewer
than eight usable words has no determinable language. It is never converted to `en`,
and never sent as `from=en` — the parameter is omitted so Azure detects instead. The
only place a concrete code is substituted is `FormVersion.source_language`, which
structurally requires one; the honest `und` stays on the source document.

### Mixed languages

A batch with several detected languages is resolved by a documented, deterministic
policy: ignore `und`, most frequent wins, ties break alphabetically. The per-language
*counts* are logged; the text never is.

## Primary and fallback metrics

Each provider is measured separately, and every counter reflects an **actual outbound
request** — selecting a provider, or a provider short-circuiting a no-op, counts as
zero:

```
primary_provider  primary_request_count  primary_retry_count
primary_duration  primary_status_class
fallback_provider fallback_request_count fallback_duration  fallback_reason
translation_total_duration  translated_character_count  untranslated_item_count
```

`fallback_reason` is one of: `timeout`, `authentication_error`, `rate_limit`,
`transport_error`, `invalid_response`, `endpoint_not_found`, `not_configured`,
`partial_response`, `missing_item`, `empty_translation`, `unsupported_language`.

A missing item falls back for **that item only** — a partial Azure response never
resends the whole batch.

## RTL field grouping

Two independent causes made an Arabic form produce 2 questions from 27 candidates:

1. **`normalize_field_name` erased non-Latin scripts**, so every Arabic label became
   the literal `"field"` and deduplication collapsed the document. The ASCII slug is
   now tried first (every German/English key stays byte-identical), with a
   Unicode-aware fallback only when ASCII yields nothing.
2. **Azure merged rows into one key-value pair.** A field label occupies one line, so
   a multi-line key is split into one candidate per line.

Geometry is direction-aware for `ar`/`he`/`fa`/`ur`: tokens are ordered by reading
position rather than ascending x, and a value region is associated with the label on
its **right**. Only ordering is direction-aware — token strings are never touched, so
Arabic characters survive byte for byte.

Stage-by-stage diagnostics make a collapse attributable without a debugger:

```
Detection stages: document=... provider=azure raw=29 normalized_distinct=29
    geometry_text=1 geometry_key_value=34 deduplicated=29 unknown_type=0
    confidence_accepted=29 rejected_below_threshold=0 rtl=True
```

## The completed form's language is no longer asked for

The upload flow's "Select completed form language" dropdown is gone. With the document's
language detected, the language a completed form must be written in is a *fact about the
form*, not a choice — a German contract is completed in German. `outputLanguage` is now
optional throughout (multipart upload, `prepare-questions`, session creation); when it is
omitted the backend resolves it from the detected document language, falling back to the
interface language only when the document's language is `und`.

The manual template flow still offers the choice, because a predefined template can genuinely
declare several `supportedOutputLanguages`.

## Frontend direction

Document direction follows the **interface** language only
(`LanguageProvider` sets `documentElement.lang` and `.dir`). An Arabic form in an
English interface stays LTR; a German form in an Arabic interface is RTL. The
provider never receives the document's language, so this is structural.

## Live results

| | Before | After |
|---|---|---|
| German: `source_language` | `en` | **`de`** (0.89 confidence, 0.04 s) |
| German: questions | 24 | 24 |
| Arabic: `source_language` | `en` | **`ar`** (0.99 confidence) |
| Arabic: raw → questions | 27 → **2** | 29 → **29** |
| Arabic: merged multi-label questions | 1 | **0** |
| Repeat request | 0.09 s, 0 calls | 0.09 s, 0 calls |

### Live results with a working Azure Translator resource

A real Translator resource was provisioned mid-session (region `germanywestcentral`).
Both endpoint forms were exercised and both work, which is why the path resolution matters:
the global endpoint (`https://api.cognitive.microsofttranslator.com`) serves `/translate`,
while a `*.cognitiveservices.azure.com` resource serves `/translator/text/v3.0/translate` and
answers **404** for a bare `/translate`. Numbers below are from the global endpoint.

**Test 1 — German contract, UI French, output auto**

| Check | Result | Target |
|---|---|---|
| `source_language` / `detected_source` | **`de`** (0.89, local detector, 0.06 s) | `de` |
| `eager_language` | `fr` | `fr` |
| Azure primary | `request_count=1 duration=0.15s status_class=2xx` | 1 call |
| Fallback | `request_count=0 reason=-` | 0 |
| `translation_total_duration` | **0.19 s** | < 3 s |
| `total_duration` | **5.36 s** | < 15 s |
| Questions | **24** | 24 |
| `untranslated_item_count` | 0 | 0 |

**Test 2 — Arabic form, UI English, output auto**

| Check | Result |
|---|---|
| `source_language` / `output_language` | **`ar`** / `ar` (auto-derived), `user_language=en` |
| Stages | `raw=29 normalized_distinct=29 deduplicated=29 rtl=True` |
| Questions | **29** (was 2) |
| Merged multi-label questions | **0** — first name, family name, date of birth, phone all separate |
| Azure primary | `request_count=1 duration=0.21s status_class=2xx`, fallback 0 |
| `total_duration` | **5.92 s** (translation 0.45 s) |
| Repeat request | **0.046 s**, session reused, zero provider calls |
| Arabic text | intact, correct order, no mojibake |

**Test 3 — German document, UI Arabic, output German**

| Check | Result |
|---|---|
| Languages | `source=de`, `user=ar`, `output=de` — all three independent |
| Questions | 24, German labels translated into Arabic (`Vermieter – Name` → `اسم المالك`, `Mieter – Name` → `اسم المستأجر`) |
| Stable choice values | unchanged (`Küche,`, `Badezimmer mit WC …`) |
| Azure primary | `request_count=1 duration=0.35s`, fallback 0 |
| Interface direction | `lang=ar`, `dir=rtl` — set from `user_language` only |

Azure Translator's own detection agrees with the local detector (German 0.97, Arabic reported
as `ar`), and is used only as the lower-precedence fallback. A deliberately mixed batch
(one German label, one Arabic label) returned per-item detections `('de', 'ar')`, which the
dominant-language policy then resolves deterministically.

## Question shape: options, compound fields, and requiredness

A third round of live testing (French application form) exposed four defects in how a
document's *semantics* survived the pipeline.

### Option groups

Selection-mark rows became one free-text question **per option** — "Non-binaire",
"Je préfère ne pas répondre", "J'accepte la déclaration" — while the question they belong
to never existed. The existing choice-group pass only recognises a group when a heading
sits directly above it, which real forms frequently omit.

`app/field_detection/option_groups.py` adds a second pass that runs on the rows the first
one did not claim, so German behaviour is untouched. Naming a group uses three sources in
descending confidence:

1. **A recognised option set** — `{femme, homme, non-binaire}` is a gender question in any
   language, and the options themselves are the evidence. Sets cover gender, employment
   status, languages, contact method, marital status and yes/no in en/de/fr/ar.
2. **The nearest section heading**, with numbering stripped ("5. Documents joints" ->
   "Documents joints").
3. **A neutral label** (`Selection group`) flagged for review — one question with an
   honest name beats N spurious text fields, and inventing a question is worse than
   admitting we do not know it.

`single_choice` vs `multiple_choice` comes from marker glyphs when they are unambiguous
(parentheses = radio, brackets = checkbox), overridden by a recognised set's own
exclusivity: you have one gender but may speak several languages.

Each row is its own group. Merging adjacent rows was tried and rejected — the French form
places languages and contact channels on consecutive rows with identical spacing under one
heading, so any geometric merge joins two unrelated questions. The existing pass now stops
accumulating when a row belongs to a *different* recognised set.

### Compound fields

"Code postal, ville" was classified `address`, whose validator demanded both a street and
a city, so `70188, Stuttgart` was rejected as invalid. Two changes:

- `classification.compound_concepts()` detects labels naming several concepts. Those that
  compose into one address (postal code + city, street + house number — including the
  German "Im Haus (Ort, Straße, Haus-Nr., Etage)") keep `address`; unrelated pairs
  ("Lieu et date", "Prénom Nom de famille", "IBAN / numéro de compte") fall back to plain
  `text`, because no single validator is correct for two different things in one box.
- The address validator now requires *one* recognisable part rather than both a street and
  a city, and returns a specific message with an example.

### Required vs optional

Every detected field defaulted to `required=True` — an assumption, not a finding, and one
that blocks a user on a field the form never insisted on.
`app/field_detection/requiredness.py` resolves three states from evidence only: the
AcroForm flag, an explicit marker word (en/de/fr/ar), a trailing asterisk, or a form-level
"all fields are required" statement. With no evidence the state is **`unknown`**, which is
recorded honestly and does *not* block progress. The evidence source and confidence are
kept so an admin can review or override.

The frontend shows "Required" (with `*`) or "Optional", and an optional question offers a
Skip control that advances without submitting.

### Normalization safety

- **Proper nouns are preserved verbatim.** `stuttgart` came back transliterated into
  Arabic. `app/answers/normalization/context.py` recognises proper-noun *labels* (person,
  place, address, employer, bank, signature, in en/de/fr/ar) and pins the answer's
  **output** value to what the user typed. Structured extraction is still kept; only the
  rendered output is fixed, and `domain-rules.md` forbids transliterating a name
  automatically.
- **Currency comes from the label.** `2000` on "Montant demandé en euros" came back as
  `USD 2000`. A currency named in the label now wins outright. When neither the label nor
  the user's answer names one, an invented currency is removed rather than trusted — but a
  currency the user actually typed ("1800 EUR monthly") is kept, because that is evidence.

### Error UX

The same validation message was rendered twice: once as a page-level banner and once under
the field. Field-level problems (HTTP 400/422) now show only next to the input; the banner
is reserved for unexpected or global failures.

### Diagnostics

```
Question shape: document=... total=38 boolean=0 single_choice=2 multiple_choice=4
    text=32 option_group_options=23 required=0 optional=0 unknown_required_state=38
Option group detected: page=1 options=4 type=radio label_source=option_set
    needs_review=False
```

Counts only — no label, option value or answer is ever logged.

### Live result (French form, Arabic UI)

| Check | Result |
|---|---|
| `source_language` | **fr** (0.39) |
| Option groups | **6** — Gender and Employment status as `single_choice`; Documents, Communication preferences, Contact method and Declarations as `multiple_choice` |
| Options folded into groups | **23** |
| Option labels leaked as text questions | **0** (was one per option) |
| "Code postal, ville" | `address` — accepts `70188, Stuttgart` |
| Requiredness | 38 `unknown`, none blocking |
| Stable values | French originals preserved; Arabic used only for display |
| Interface | RTL, Arabic labels |
| Total duration | 4.64 s |

## Known limitations

- **The endpoint must be a Translator resource, and it must use the right path.** A Document
  Intelligence endpoint answers **404** for `/translate`; a `*.cognitiveservices.azure.com`
  Translator resource serves `/translator/text/v3.0/translate` and answers 404 for a bare
  `/translate`. Both are handled, and a 404 is reported as `endpoint_not_found` rather than a
  transient failure, but the wrong resource still cannot authenticate.
- `docker compose restart` does **not** re-read `.env`. Use `docker compose up -d
  --force-recreate` after changing credentials, or the container keeps the old values while the
  file on disk looks correct.
- The local detector covers Latin-script European languages and the major non-Latin scripts.
  It is not a general-purpose language identifier.
- RTL geometry improves ordering and label association, but Azure's key-value grouping remains
  the dominant signal for Arabic forms — the local text passes contribute only one candidate
  there.
- The translation cache is process-local and dropped on restart.
- **A long wrapped checklist splits into one question per row.** One question per row is
  occasionally too granular, but it is never *wrong* in the way a merge would be — see the
  languages/contact-channel case above.
- **Azure Translator mistranslates some isolated single words.** `Français` -> `الإنجليزية`
  ("English") was verified directly against the provider with correct per-item ids and
  `detectedLanguage: fr`, so this is provider translation quality on a one-word input, not
  an id-mapping fault. Stable option *values* are unaffected: only the display label is
  translated.
- **Azure Document Intelligence F0 rate-limits the E2E suite.** Uploading many PDFs in
  quick succession returns `HTTP 429`, which surfaces as "We could not process this
  document". Affected specs pass when re-run after a pause. A paid tier removes it.
- Progress and completion now count every question, not only mandatory ones — a direct
  consequence of evidence-based requiredness, and the reason `ProgressInfo` gained
  `totalQuestions`/`answeredQuestions`.
- Requiredness has no per-field admin override yet; the evidence and confidence are
  recorded for the review UI that Phase 16 will add.
