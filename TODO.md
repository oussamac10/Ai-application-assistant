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

## Blocked

**Live Azure Translator verification.** `AZURE_TRANSLATOR_API_KEY` is not provisioned, so:

- every Azure test in `tests/translation/test_azure_translator.py` is mocked (26 tests covering
  positional mapping, partial/malformed/short/long responses, auth failure, rate limiting, timeout,
  transport error, retry, chunking and secret handling), and
- the benchmark above ran with `TRANSLATION_PROVIDER=ollama`.

To close it: create a **Translator** resource in the Azure Portal, put `AZURE_TRANSLATOR_API_KEY`
and `AZURE_TRANSLATOR_REGION` in the git-ignored root `.env`, set `TRANSLATION_PROVIDER=azure` and
`TRANSLATION_FALLBACK_PROVIDER=ollama`, restart the backend and re-run both benchmarks. Expect one
provider call per document and `detected_source=de` on the rental contract.

## Carried Deferred Items

- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10).
- Pre-existing Ruff formatting exceptions under `app/documents/*` and `tests/documents/`.
- Preparation is still synchronous; background jobs with progress polling remain Phase 20.
- The translation cache is process-local and dropped on restart.
- Arabic field *detection* quality (2 fields from 27 candidates, merged labels) — a Phase 13/14
  heuristics limitation with RTL layout, not a translation issue.
- With Ollama selected, a German document in an English interface is still not translated: the
  local model cannot detect a source language. Only Azure resolves this.
