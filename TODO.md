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
| `POST /prepare-questions` | `status: "ready"`, `errorCode: null`, ~40 s (first call) |
| Guided questions generated | **19** |
| First guided question served | `vermieter_name` ("Mietvermieter – Name"), 19 required fields |
| Landlord vs tenant distinct | yes — `vermieter_name` **and** `mieter_name` |
| Bank block | `kontoinhaber`, `bank`, `iban`, `bic` all present |
| Dates / amounts | 3 × `date`, 4 × `money` from sentence-embedded blanks |
| Second `prepare-questions` | same `sessionId`, `reusedExistingSession: true`, 0.1 s |
| Live Azure calls | **exactly 1** (`served_from_cache=false` rows = 1) |
| Usage record | `provider=azure model=prebuilt-layout pages=2 duration=4.0s succeeded=true request_id=84037c21-…` |
| Secret leakage | API key and endpoint absent from backend logs |
| Raw review screen shown | no — normal guided flow only |

**F0 free-tier truncation confirmed:** the usage record shows `pages=2` for a 3-page
document, i.e. Azure analyzed only the first two pages, exactly as the tier documents. The
contract's meaningful fields are on pages 1–2, so the question set is unaffected here, but a
document with content on page 3+ would lose it on F0.

## Verification

Run locally via `backend/venv/bin/python`:

- `PYTHONPATH=. venv/bin/python -m pytest -q` → **433 passed** (383 before + 50 new Azure tests)
- `venv/bin/python -m ruff check .` → All checks passed
- `venv/bin/python -m ruff format --check` on changed files → clean
- `venv/bin/python -m mypy app` → Success, no issues in 135 source files
- `alembic upgrade head` / `downgrade -1` / `upgrade head` → clean round-trip
  (`40175fb1902b`: `provider_usage_records` + `detection_fingerprint`)
- Frontend `npm test` / `lint` / `typecheck` → unchanged and clean (no frontend code changed)
- Azure fixture through the full pipeline → 19 candidates, 19 usable, `vermieter_name` and
  `mieter_name` distinct, one Azure call, second request served from cache

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
- The app's own `logger.info` diagnostics are not emitted to stdout under uvicorn's default
  logging config (pre-existing), so the Azure request-id line is only visible in the
  `provider_usage_records` table, not the container logs.

## Carried Deferred Items

- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10).
- Pre-existing Ruff formatting exceptions under `app/documents/*` and `tests/documents/`.
