# Project TODO

## Completed Phases

| Phase | Branch | Status |
|---|---|---|
| 1 — Project Foundation | `main` | ✅ Done |
| 2 — Form Definitions and Versioning | `feature/form-definitions-versioning` | ✅ Done |
| 3 — Temporary Anonymous Sessions | `feature/anonymous-sessions` | ✅ Done |
| 4 — Mock Question and Answer Workflow | `feature/mock-qa-workflow` | ✅ Done |
| 5 — Local AI Integration with Ollama | `feature/local-ai-ollama` | ✅ Done |
| 6 — Reusable Question Catalog and Hybrid Resolution | `feature/question-catalog-hybrid-resolution` | ✅ Done |
| 7 — Frontend Guided Form Experience | `feature/frontend-guided-experience` | ✅ Done |
| 8 — PDF Template Mapping and Export | `feature/pdf-template-export` | ✅ Done |
| 9 — Form Upload and Document Analysis | `feature/form-upload-analysis` | ✅ Done |
| 10 — OCR Integration | `feature/ocr-integration` | ✅ Done |
| 11 — Dynamic Field Detection | `feature/dynamic-field-detection` | ✅ Done |
| 12 — User Accounts and Persistent Sessions | `feature/user-accounts-persistent-sessions` | ✅ Done |
| 13 — Automatic Upload-to-Questions User Flow | `feature/automatic-upload-to-questions` | ✅ Done |

Archived phase TODOs live under `docs/progress/`. The full plan is in `docs/roadmap.md`.

---

## Current Task

**Phase 14 — Azure Document Intelligence Provider.** Branch: `feature/azure-document-intelligence`.
Base: `feature/automatic-upload-to-questions`.
**Status: Complete — verified against the live Azure service.**

## Goal

Add Azure Document Intelligence as a second, opt-in field-detection provider alongside the local
detector, and prove Azure output converts into the app's existing internal detected-field format.
The local provider stays the default. Hybrid/fallback between providers is Phase 15.

## Acceptance Criteria

- [x] `AZURE_DOCUMENT_INTELLIGENCE_*` backend-only config; key never reaches the frontend or logs
- [x] Validation fails fast when Azure is selected, and is inert for local/mock
- [x] `FIELD_DETECTION_PROVIDER=azure` in the factory (mock | local | azure — no hybrid mode)
- [x] Provider implements the existing `FieldDetectionProvider` contract unchanged
- [x] Submit PDF, poll the operation, bounded timeout + retries, safe error mapping, request id kept
- [x] Azure output normalized into internal models — no SDK object enters the workflow
- [x] Polygon→bounding-box conversion (inch / pixel / normalized, rotation, multiple/missing polygons)
- [x] Candidates from key-value pairs, selection marks, and the shared text passes
- [x] Headings / legal prose / footnotes never become fields; one malformed item never fails the document
- [x] Phase 13 deterministic routing reused unchanged; Azure confidence is only an input
- [x] `prepare-questions` orchestration, ownership, idempotency and resume all unchanged
- [x] Safe Azure error codes mapped to generic user-facing messages
- [x] Usage/cost metadata persisted per request (+ migration)
- [x] Detection cached on (checksum, provider, model, analysis version) — no duplicate Azure call
- [x] Mocked backend tests; no automated test contacts Azure
- [x] ADR 0013, phase doc, roadmap, architecture/security/privacy/field-detection/README updates
- [x] **Live-service manual verification with the German rental-contract PDF** — done, see below

## Live verification (real Azure endpoint)

Run against `Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf` with
`FIELD_DETECTION_PROVIDER=azure`, resource
`ai-form-assistant-document-intelligence-dev`, model `prebuilt-layout`,
api-version `2024-11-30`:

| Check | Result |
|---|---|
| `POST /prepare-questions` | `status: "ready"`, `errorCode: null`, HTTP **200** through the Next proxy, 43.8 s |
| Guided questions generated | **24** |
| First guided question served | `vermieter_name` ("Vermieter – Name"), 24 required fields |
| Landlord vs tenant distinct | yes — `vermieter_name` **and** `mieter_name` |
| Bank block | `kontoinhaber`, `bank`, `iban`, `bic` all present |
| Dates / amounts | 3 × `date`, 4 × `money` from sentence-embedded blanks |
| Second `prepare-questions` | same `sessionId`, `reusedExistingSession: true`, **0.09 s, 0 AI calls** |
| Ollama calls for question generation | **4** (was 28 — batched, deduplicated, cached) |
| Live Azure calls | **exactly 1** (`served_from_cache=false` rows = 1) |
| Usage record | `provider=azure model=prebuilt-layout pages=2 duration=4.0s succeeded=true request_id=84037c21-…` |
| Secret leakage | API key and endpoint absent from backend logs |
| Raw review screen shown | no — normal guided flow only |

**F0 free-tier truncation confirmed:** the usage record shows `pages=2` for a 3-page
document, i.e. Azure analyzed only the first two pages, exactly as the tier documents. The
contract's meaningful fields are on pages 1–2, so the question set is unaffected here, but a
document with content on page 3+ would lose it on F0.

## Request duration and frontend state

The 500 the frontend received was Next.js's rewrite proxy abandoning the request after its
default 30 s, not a backend failure (`Failed to proxy … socket hang up`; body was plain-text
`Internal Server Error`, not the API's `{code, message, stage}` JSON). The backend completed
successfully after the proxy had already answered. Full analysis in
[ADR 0014](docs/decisions/0014-batched-translation-and-request-duration.md).

Measured on the reference PDF, fresh upload each time, through the proxy at `:3003`:

| | before | after |
|---|---|---|
| HTTP status | 500 | 200 |
| total request duration | 30.08 s (abandoned at the ceiling) | 43.84 s (completed) |
| Ollama calls | 28 | 4 |
| generated questions | 24 (never delivered) | 24 |
| frontend result | processing error | first question `vermieter_name` |
| repeat request | — | 0.09 s, 0 AI calls, session reused |

Stage breakdown from the structured timing logs of the "after" run:

| Stage | Duration |
|---|---|
| `azure_duration` | 8.77 s |
| `normalization_duration` | 0.01 s |
| `detection_duration` (provider + normalization + persistence) | 8.90 s |
| `translation_duration` | 34.27 s |
| `question_resolution_duration` (translation + fields + publish + session) | 34.88 s |
| `ocr_duration` | 0.00 s (digital PDF) |
| `total_duration` | 43.80 s |

`ollama_call_count=4` for `unique_texts=28`: three batched calls of 12/12/4 plus one per-item
fallback. One batch entry came back as `"id": ": 1"` and was dropped individually — the earlier
whole-response validation discarded all four entries of that chunk instead.

## Verification

Run locally via `backend/venv/bin/python`:

- `PYTHONPATH=. venv/bin/python -m pytest -q` → **474 passed** (433 Azure baseline + 12 batch
  translation + 9 Ollama batch wire contract + 4 concurrency + 4 bridge batching/idempotency,
  plus the 12 language-combination and positional-dedup tests added earlier this phase)
- `venv/bin/python -m ruff check .` → All checks passed
- `venv/bin/python -m ruff format --check` on changed files → clean
- `venv/bin/python -m mypy app` → Success, no issues in 135 source files
- `alembic upgrade head` / `downgrade -1` / `upgrade head` → clean round-trip
  (`40175fb1902b`: `provider_usage_records` + `detection_fingerprint`)
- Frontend `npm test` → **129 passed** (124 + 5 request-dedup); `lint` and `typecheck` clean
- Azure fixture through the full pipeline → 19 candidates, 19 usable, `vermieter_name` and
  `mieter_name` distinct, one Azure call, second request served from cache

- Playwright (CI mode, rebuilt Docker, `azure`/`ollama` providers): **25 passed, 2 flaky**
  (passed on retry), **1 pre-existing failure** (`guided-flow.spec.ts` default-tab gap, carried
  since Phase 9). Two Phase 12 auth specs failed on the first full run because the backend pytest
  suite — run concurrently by mistake — `TRUNCATE`s `form_templates` and wiped the
  `basic-registration` fixture mid-suite; both pass when re-run with the fixture present
  (`2 passed`). Do not run pytest and Playwright against the same dev database at once.

## Known Limitations

- F0 free tier analyzes only the first 2 pages per document (confirmed live: `pages=2` for a 3-page file).
- `prebuilt-layout` does not always return `keyValuePairs`; detection then falls back to the
  shared text passes (local parity + selection marks).
- Scanned PDFs still run the Phase 10 OCR step first; using Azure instead of OCR is Phase 15.
- No fallback on Azure failure — the document fails with the generic processing error (Phase 15).
- `estimated_cost` recorded as NULL until Phase 18 defines pricing.
- Azure typed `PLZ, Ort` and `BIC` as `multiline_text` where the local provider says
  `address`/`string` — Azure's word boxes differ slightly, so the "large blank gap below"
  heuristic fires. Cosmetic (a textarea instead of a single-line input); noted for Phase 15.
- Most of the 34 s translation cost is avoidable: the contract is German, but detected text is
  *assumed* to be the default source language (`en`), so German labels take an `en -> de` round
  trip that mostly returns them unchanged. Document-language detection would remove it, but that
  changes detection behaviour and is out of scope here.
- Preparation is still synchronous (43.8 s). Background processing with progress polling is
  Phase 17; this phase only made the synchronous path complete honestly.
- The translation cache is process-local and dropped on restart. No user data is stored in it.
- `experimental.proxyTimeout` is the documented Next 14 knob but is an experimental option.

## Carried Deferred Items

- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10).
- Pre-existing Ruff formatting exceptions under `app/documents/*` and `tests/documents/`.
