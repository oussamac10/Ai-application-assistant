# TODO

## Completed Phases

Archived under `docs/progress/`:

1. Project Foundation
2. Form Definitions and Versioning
3. Temporary Anonymous Sessions
4. Mock Question and Answer Workflow
5. Local AI Integration with Ollama
6. Reusable Question Catalog and Hybrid Resolution
7. Frontend Guided Form Experience
8. PDF Template Mapping and Export
9. Form Upload and Document Analysis
10. OCR Integration
11. Dynamic Form Field Detection
12. User Accounts and Saved Applications
13. Automatic Upload-to-Questions User Flow
14. Azure Document Intelligence Provider

## Current Task

Phase 15 — Azure Translator Integration. Branch `feature/azure-translator`, based on
`feature/azure-document-intelligence`.

**Status: implemented; live Azure verification blocked.** Everything below is built, tested and
documented. The one thing that cannot be closed from here is a live Azure Translator run — no
`AZURE_TRANSLATOR_API_KEY` is provisioned, so all Azure tests are mocked and the benchmark ran on
the Ollama provider. See "Blocked" at the end.

## Goal

Extract the `TranslationProvider` abstraction named in `docs/claude/domain-rules.md`, and implement
Azure Translator behind it as the provider for translating question labels, choice options and
other display text — replacing the local model for that specific job.

## Confirmed implementation decisions

1. Azure Translator is the primary translation provider when configured.
2. Ollama remains available as a selectable fallback provider.
3. Azure automatic source-language detection is included in Phase 15 to avoid incorrect and wasteful
   forced `en -> target` translation paths for non-English source documents.
4. Approved catalog translations, persisted translations, and cache hits must still win before any
   provider call.
5. Only the current user-interface language is translated eagerly during question preparation.
6. Output-language translation remains deferred until it is actually needed by review or export.
7. Real Azure credentials stay in the git-ignored root `.env`; `.env.example` contains empty
   placeholders only.
8. Automated tests must mock Azure and must never call the live service.

## Why this phase, in one paragraph

Translation currently rides on `AIProvider`, which conflates language understanding (extraction,
clarification, question generation) with plain text translation. Phase 14's measurements make the
cost of that conflation concrete: on the reference German rental contract, `prepare-questions`
takes **43.8 s**, of which **34.3 s** is local-model translation — and that is *after* batching cut
the call count from 28 to 4. The remaining time is the model generating text, which a dedicated
translation service does in a single array request.

## Starting point (measured, Phase 14)

| | value |
|---|---|
| `total_duration` | 43.80 s |
| `translation_duration` | 34.27 s (78% of the request) |
| `ollama_call_count` | 4 (3 batched chunks + 1 per-item fallback) |
| `unique_texts` | 28 |
| generated questions | 24 |
| repeat request | 0.09 s, 0 AI calls, session reused |

These are the numbers Phase 15 has to improve on, and the same measurement should be repeated at
the end for a like-for-like before/after.

## Implementation checklist

- [x] Add a `TranslationProvider` protocol and provider factory.
- [x] Keep deterministic mock and Ollama translation implementations.
- [x] Add `AzureTranslatorProvider` using one array request per target language when possible.
- [x] Add backend-only `AZURE_TRANSLATOR_*` configuration and Docker passthrough.
- [x] Validate Azure configuration only when Azure is selected (primary *or* fallback).
- [x] Add bounded timeout, one bounded retry, safe error mapping, and request-ID capture.
- [x] Map positional Azure results back to stable caller IDs explicitly.
- [x] Validate partial, missing, duplicate, and malformed results per item.
- [x] Preserve approved-catalog, persisted-translation, cache, and deterministic fallback order.
- [x] Add source-language auto-detection while preserving the detected source metadata.
- [x] Translate only the current user language eagerly.
- [x] Keep output-language translation deferred (`app/translation/backfill.py`).
- [x] Record request count, translated character count, cache hits, provider latency, fallbacks.
- [x] Ensure API keys and raw provider responses never appear in logs or frontend responses.
- [x] Add unit, integration, regression, RTL, and idempotency tests.
- [x] Update ADR, phase docs, architecture, security, privacy, README, `.env.example`, compose.
- [x] Benchmark the German rental contract before and after.
- [x] Test the Arabic digital form and verify Arabic/RTL behavior.
- [x] Run backend and frontend quality gates.
- [ ] **Live Azure Translator run** — blocked on credentials, see below.

## Deterministic protection (new)

`app/translation/protected.py` withholds text that is *entirely* an identifier: email addresses,
IBANs (matched with spaces removed — forms print them grouped), BICs, ISO/numeric dates, phone
numbers, currency amounts, URLs, UUIDs and internal keys. Conservative on purpose: "IBAN des
Vermieters" and "Date of birth" are ordinary labels and must still be translated. Two false
positives were caught by tests while writing it — a space-grouped IBAN escaped the first pattern,
and hyphenated German words ("E-Mail-Adresse") were misread as machine tokens.

Names are not pattern-matched (no reliable way to tell a name from a common noun, and
`domain-rules.md` forbids automatic transliteration); user-entered values never enter this
pipeline at all.

## Benchmark (measured)

German rental contract, fresh upload, through the Next proxy,
`FIELD_DETECTION_PROVIDER=azure` + `TRANSLATION_PROVIDER=ollama`:

| | Phase 14 | Phase 15 | Target | |
|---|---|---|---|---|
| `total_duration` | 43.80 s | **5.20 s** | < 15 s | met |
| `translation_duration` | 34.27 s | **0.04 s** | < 3 s | met |
| provider calls | 4 | **0** | — | |
| `unique_texts` | 28 | 28 | — | |
| generated questions | 24 | 24 | 24 | met |
| repeat request | 0.09 s, 0 calls | **0.05 s, 0 calls** | 0 calls | met |

Stage split of the Phase 15 run: `azure_duration=4.67s` (fresh detection call),
`normalization_duration=0.01s`, `detection_duration=4.80s`, `translation_duration=0.04s`,
`question_resolution_duration=0.39s`, `total_duration=5.20s`. First question still
`vermieter_name` / "Vermieter – Name".

**Read the gain honestly:** it comes from deferring the output language, not from Azure
Translator. With Ollama selected and the interface language equal to the assumed source language,
the pipeline correctly concludes there is nothing to translate and makes zero calls. The Azure
path would make exactly one call and would additionally translate the German labels into English —
which Ollama cannot do, because it cannot detect a source language.

## Arabic form (`arabic_test_form.pdf`)

| Check | Result |
|---|---|
| `prepare-questions` | `status: ready`, HTTP 200, 11.52 s |
| Arabic character integrity | intact — no corruption, no mojibake |
| Questions generated | **2** (from 27 raw candidates) |
| Detected/recorded source language | `en` (Ollama cannot detect; Azure would report `ar`) |
| RTL | unchanged — `LanguageProvider` sets `document.documentElement.dir`, covered by existing tests |
| Identifiers translated | none |

The low question count is a **field-detection** limitation, not a translation one: the blank-run
and section-context heuristics from Phases 13/14 are tuned for LTR German/English layout, and here
three separate Arabic labels were merged into a single field. Out of scope for this phase, and
recorded as a carried item.

## Verification

Backend (`backend/venv/bin/python`):

- `PYTHONPATH=. venv/bin/python -m pytest -q` → **574 passed**
  (503 Phase 14 baseline after removing the superseded `test_batch_translation.py`, plus 19
  factory + 26 Azure Translator + 21 pipeline + 19 protected-text + 15 bridge/translation tests)
- `venv/bin/python -m ruff check .` → All checks passed
- `venv/bin/python -m ruff format --check` on changed files → clean
- `venv/bin/python -m mypy app` → Success, no issues in 146 source files
- No migration needed: Phase 15 adds no schema.

Frontend: `npm test` → **129 passed** (17 files), `npm run lint` and `npm run typecheck` clean.
No frontend source changed this phase; RTL is unchanged and still covered by
`form-session.test.tsx` and `application-select-manually.test.tsx`.

Playwright (CI mode, `azure` detection + `ollama` translation): **27 passed, 3 failed** at
`--timeout=60000 --retries=0`. Two of those three pass at the project's normal 120 s timeout —
re-running `dynamic-field-detection-flow.spec.ts` alone gives **5 passed (35.1 s)**, including
"German user language: question and choice labels are translated, submitted values stay stable"
and "Arabic user language: RTL stays active and stable option values are unchanged". They time out
at 20 s in `page.waitForURL` because the real pipeline (fresh Azure detection plus Ollama
translation for a non-English interface) exceeds that budget; both were already recorded as flaky
in Phase 14. The remaining failure is `guided-flow.spec.ts`, pre-existing since Phase 9.

One test self-skips: `upload-analysis-flow.spec.ts:255` reports "Fixture PDF not found".

**Process note:** two earlier attempts at this suite were invalidated because the backend pytest
suite was run concurrently — it `TRUNCATE`s `form_templates` and wipes the `basic-registration`
fixture mid-run, which surfaces as unrelated failures in the Phase 12 auth specs. Never run pytest
and Playwright against the same dev database at once.

## Live-testing follow-up (second round)

Four defects surfaced with `TRANSLATION_PROVIDER=azure`. Three were code bugs; the fourth was a
configuration problem the third had been hiding.

### Root causes

| Symptom | Cause |
|---|---|
| German reported as `en`, Arabic as `en` | No document-language detection existed. Ollama's *assumed* language was recorded as if it were a detection, and Azure metadata only exists as a side effect of translating. |
| `provider=azure provider_latency=42.62s` | One combined latency field. Azure was failing in ~0.15 s; Ollama was spending the 42.6 s. |
| `provider_calls=1 characters=0 latency=0.00s` | Counters incremented on provider *selection*, not on an outbound request. |
| 27 Arabic candidates → 2 questions | `normalize_field_name` stripped non-ASCII, so every Arabic label became the literal `"field"` and deduplication collapsed the document. Separately, Azure merged three rows into one key-value pair. |

### Fixes

- [x] `app/language/` — `DocumentLanguageDetector`, local + mock implementations, filtered sampling,
      persistence on `source_documents` (migration `e1975a7403eb`), reuse, precedence, `und`.
- [x] `TranslationUsage.source_language_is_detected` — an assumption can no longer outvote a real
      detection.
- [x] Separate primary/fallback metrics + `fallback_reason`; counters come from real outbound
      requests; a failed call reports its own cost.
- [x] `from` omitted for `und`; sent only for a trusted source language.
- [x] Azure custom-subdomain path (`/translator/text/v3.0/translate`) and a distinct
      `endpoint_not_found` code for 404 (not retried — a wrong endpoint will not fix itself).
- [x] `normalize_field_name`: ASCII slug first (German/English byte-identical), Unicode fallback,
      deterministic hash for punctuation-only labels.
- [x] Multi-line Azure key-value keys split into one candidate per line.
- [x] Direction-aware geometry for `ar`/`he`/`fa`/`ur` (reading-order tokens, label on the right).
- [x] Stage-by-stage detection diagnostics.
- [x] `tests/conftest.py` pins providers so the suite never calls a live service — it had begun
      doing so once `.env` selected Azure, hanging for minutes on timeouts.

### Live verification

**Test 1 — German contract, UI French, output German**

| Check | Result |
|---|---|
| `source_language` | **`de`** (was `en`), confidence 0.89, detected in 0.04 s |
| `eager_language` / `deferred_languages` | `fr` / `-` |
| Questions | **24** |
| Azure primary | `request_count=1 duration=0.14s status_class=4xx` |
| Fallback | `ollama request_count=3 duration=46.37s reason=authentication_error` |
| Total | 51.75 s |

The latency target is missed, and the logs now say exactly why: Azure rejects the credential in
0.14 s and Ollama does all the work. That is the credential blocker below, not a code defect.

**Test 2 — Arabic form, UI English, output Arabic**

| Check | Result |
|---|---|
| `source_language` | **`ar`** (was `en`), confidence 0.99, `rtl=True` |
| Stages | `raw=29 normalized_distinct=29 deduplicated=29` (was 27 → 2) |
| Questions | **29** (was 2) |
| Merged multi-label questions | **0** — family name, place of birth and postal code are separate |
| Arabic text | intact, correct word order, no mojibake |
| Repeat request | 0.089 s, **0 provider calls**, session reused |

**Test 3 — interface direction** — `LanguageProvider` sets `lang`/`dir` from `user_language`
only; covered by `language-direction.test.tsx` (4 tests).

## Live verification with a working Azure Translator (final)

A Translator resource was provisioned during the session. Both endpoint forms were exercised;
the global endpoint is the final configuration.

| | Test 1 — German (UI fr) | Test 2 — Arabic (UI en) | Test 3 — German (UI ar) |
|---|---|---|---|
| `source_language` | **de** (0.89) | **ar** (0.99) | de |
| `user_language` | fr | en | ar |
| `output_language` | de (auto) | ar (auto) | de |
| Azure primary | 1 req, 0.15 s, `2xx` | 1 req, 0.21 s, `2xx` | 1 req, 0.35 s, `2xx` |
| Fallback | 0 | 0 | 0 |
| Translation total | **0.19 s** | **0.45 s** | 0.40 s |
| Total duration | **5.36 s** | **5.92 s** | 5.35 s |
| Questions | **24** | **29** (was 2) | 24 |
| Untranslated items | 0 | 0 | 0 |
| Merged multi-label questions | — | **0** | — |
| Repeat request | 0.046 s, 0 provider calls | 0.046 s, 0 provider calls | — |

Every target met: translation well under 3 s, total well under 15 s, one Azure array request per
document, no fallback, and a repeat request costs nothing.

Stable choice values are unchanged (`Küche,`, `Badezimmer mit WC …`), landlord and tenant stay
distinct in Arabic (`اسم المالك` / `اسم المستأجر`), and Arabic text is byte-intact.

## Output-language selector removed

The upload flow no longer asks "Select completed form language". With the document's language
detected, the completed form's language is a fact about the form, not a user choice.
`outputLanguage` is optional across the multipart upload, `prepare-questions` and session
creation; when omitted the backend resolves it from the detected language, falling back to the
interface language only for `und`. The manual template flow keeps the choice, because a template
can genuinely declare several `supportedOutputLanguages`.

## Question-shape follow-up (third round)

Live French-form testing showed the pipeline preserving a document's *text* but losing its
*semantics*.

| Problem | Cause | Fix |
|---|---|---|
| Options became individual text questions | The choice pass needs a heading directly above; real forms omit it | `option_groups.py` second pass on unclaimed rows |
| Parent questions missing | Nothing inferred a group name | Recognised option sets -> heading -> neutral+review |
| Languages merged with contact channels | Adjacent rows accumulated into one group | Stop accumulating at a different recognised set |
| `70188, Stuttgart` rejected | `address` validator demanded street *and* city | Require one recognisable part; compound labels detected |
| `stuttgart` transliterated | AI normalized without field context | Proper-noun labels pin the output value verbatim |
| `2000` became `USD 2000` | No currency context | Label wins; invented currency removed; typed currency kept |
| Every field required | Defaulted to `True` | Three-state evidence-based detection; `unknown` never blocks |
| Validation error shown twice | One `errorMsg` fed banner and field | Field-level vs global separation |

### Live verification — French form, Arabic UI

| Check | Result |
|---|---|
| `source_language` | **fr** (0.39) — French detection fixed by weighting shared function words |
| Option groups | **6**: Gender + Employment status (`single_choice`), Documents, Communication preferences, Contact method, Declarations (`multiple_choice`) |
| Options folded into groups | **23** |
| Option labels leaked as text questions | **0** |
| "Code postal, ville" | `address`, accepts `70188, Stuttgart` |
| Requiredness | 38 `unknown`, none blocking; UI shows Required/Optional with Skip |
| Stable option values | French originals preserved, Arabic for display only |
| Total duration | 4.64 s |

German and Arabic forms unchanged (`Mietraum / Mieträume` group intact, 21 German
candidates, Arabic 29 questions).

### Quality gates (run sequentially)

- Backend `pytest` → **755 passed**; ruff and `ruff format --check` clean; mypy clean
  (154 files).
- Frontend `npm test` → **133 passed** (18 files); lint and typecheck clean.
- Playwright → **26 passed, 3 failed, 1 flaky**. Two of the three are Azure Document
  Intelligence **F0 free-tier rate limiting** (`HTTP 429 Too Many Requests`) triggered by the
  suite uploading many PDFs in quick succession — verified in the backend log
  (`azure_rate_limited`), and both pass when re-run after a pause (the multiple-choice spec
  alone: `1 passed (13.1s)`). The third is `guided-flow.spec.ts`, pre-existing since Phase 9.

### Two regressions this work introduced, found and fixed

- **"Question 1 of 0 (100%)".** Progress counted only *required* fields, so an
  evidence-based form that marks nothing mandatory reported a total of zero.
  `ProgressInfo` gained `totalQuestions` / `answeredQuestions`; `totalRequiredFields` keeps
  its own meaning for completion checks, and the frontend now reads the new fields.
- **The summary was unreachable.** Completion also keyed off required fields only, so a
  form with none never advanced. It now completes when every question is answered.

### Tests added

`test_option_groups.py` (25), `test_requiredness.py` (18), `test_normalization_context.py`
(41 across currency and proper nouns), plus compound-label cases in `test_classification.py`.

## Carried Deferred Items

- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10).
- Pre-existing Ruff formatting exceptions under `app/documents/*` and `tests/documents/`.
- Preparation is still synchronous; background jobs with progress polling remain Phase 20.
- The translation cache is process-local and dropped on restart.
- A long wrapped checklist splits into one question per row (never merged — see above).
- Azure mistranslates some isolated one-word options (`Français` -> `الإنجليزية`), verified
  against the provider with correct ids; stable values are unaffected.
- Requiredness has no per-field admin override until Phase 16.
- Arabic field *detection* quality (2 fields from 27 candidates, merged labels) — a Phase 13/14
  heuristics limitation with RTL layout, not a translation issue.
- With Ollama selected, a German document in an English interface is still not translated: the
  local model cannot detect a source language. Only Azure resolves this.
