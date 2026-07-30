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
**Status: Implemented — live-service verification outstanding (no Azure credentials available).**

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
- [ ] **Live-service manual verification with the German rental-contract PDF** — blocked, see below

## Blocker

No Azure endpoint or API key is available in this environment, so the real service has never been
called. Requirement 12/16 (the exact `Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf` processed by
live Azure through `FIELD_DETECTION_PROVIDER=azure`) therefore remains unverified. Exact steps to
run once credentials exist are in `docs/phases/phase-14-azure-document-intelligence.md`
("Manual verification").

What *was* verified instead: a `prebuilt-layout`-shaped `analyzeResult` whose words and polygons
were generated from that same PDF's own text layer, driven through the real provider,
normalization, confidence routing, question generation and session creation end-to-end.

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

- Live Azure never called (above).
- F0 free tier analyzes only the first 2 pages per document.
- `prebuilt-layout` does not always return `keyValuePairs`; detection then falls back to the
  shared text passes (local parity + selection marks).
- Scanned PDFs still run the Phase 10 OCR step first; using Azure instead of OCR is Phase 15.
- No fallback on Azure failure — the document fails with the generic processing error (Phase 15).
- `estimated_cost` recorded as NULL until Phase 18 defines pricing.

## Carried Deferred Items

- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10).
- Pre-existing Ruff formatting exceptions under `app/documents/*` and `tests/documents/`.
