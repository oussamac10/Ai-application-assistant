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

---

## Current Task

**Phase 10 — OCR Integration.** Branch: `feature/ocr-integration`. Base: `feature/form-upload-analysis`.

## Goal

Implement secure local OCR for uploaded source documents that Phase 9 classified as scanned or OCR-required. Persist normalized page-level OCR results (text, lines, words, bounding boxes, confidence) for Phase 11 to consume. No arbitrary field detection or form-definition generation.

## Acceptance Criteria

See `docs/claude/current-phase.md` for full in-scope/out-of-scope breakdown. Summary:

- [ ] OCR provider interface (`OCRProvider` protocol)
- [ ] deterministic `MockOCRProvider`
- [ ] `LocalOCRProvider` (PyMuPDF render + pytesseract)
- [ ] page rendering, rotation-aware, private temp storage, cleaned up
- [ ] persisted `OCRResult` model + reversible Alembic migration
- [ ] ownership + expiration + eligibility checks reused from Phase 9
- [ ] idempotent OCR API (`POST`/`GET /api/source-documents/{id}/ocr`)
- [ ] frontend OCR status/result UI, all 4 languages, RTL preserved
- [ ] cleanup command extended for expired OCR data and temp images
- [ ] backend, frontend, and Playwright tests
- [ ] ADR 0009, `docs/ocr.md`, updated docs
- [ ] Ruff, mypy, ESLint, TypeScript all pass
- [ ] Phase 7, 8, 9 regressions preserved

## Planned Steps

- [ ] Inspect Phase 9 `backend/app/documents/` module to reuse ownership/expiration/storage patterns
- [ ] Add `backend/app/ocr/` module (models, schemas, repository, service, providers, renderer, normalization, validation, errors, routes)
- [ ] Add OCR config to `backend/app/core/config.py`, `.env.example`, `docker-compose.yml`, `backend/Dockerfile`
- [ ] Add Alembic migration for `OCRResult`; verify upgrade/downgrade/upgrade
- [ ] Implement `MockOCRProvider` and backend tests first (TDD), then `LocalOCRProvider`
- [ ] Implement OCR API routes + idempotency + error contracts
- [ ] Extend cleanup command for OCR expiration/temp files
- [ ] Add frontend `features/document-ocr/` UI + localization (en/de/fr/ar)
- [ ] Add Playwright `e2e/ocr-flow.spec.ts`
- [ ] Write ADR 0009 and update docs
- [ ] Full verification pass (ruff, mypy, pytest, lint, typecheck, vitest, playwright)

## Files Expected to Change

- `backend/app/ocr/**` (new)
- `backend/app/core/config.py`
- `backend/migrations/versions/*` (new)
- `backend/app/commands/` (cleanup extension)
- `backend/Dockerfile`, `docker-compose.yml`, `.env.example`
- `frontend/src/features/document-ocr/**` (new)
- `frontend/messages/{en,de,fr,ar}.json`
- `frontend/e2e/ocr-flow.spec.ts` (new)
- `docs/ocr.md`, `docs/decisions/0009-local-ocr-provider.md` (new)
- `docs/architecture.md`, `docs/workflow.md`, `docs/testing.md`, `docs/security.md`, `docs/privacy.md`, `docs/document-upload-analysis.md`

This list is an initial estimate and may be updated during implementation.

## Decisions and Assumptions

- OCR remains local only; no cloud OCR in this phase.
- Supported OCR languages limited to English, German, French, Arabic.
- Coordinates are persisted in rendered-image space, not PDF point space.
- Field/label semantics are explicitly out of scope (deferred to Phase 11).

## Blockers

- None

## Verification

- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Linting passes
- [ ] Formatting passes
- [ ] Type checking passes
- [ ] Playwright OCR flow passes
- [ ] Migration upgrade/downgrade verified
- [ ] Acceptance criteria manually verified

---

## Pre-Implementation Verification (deferred Phase 9 checks)

Verified on `feature/ocr-integration` before starting Phase 10 implementation:

- [x] mypy — `mypy app` → **Success: no issues found in 77 source files**
- [x] Alembic downgrade/re-upgrade — `alembic downgrade -1` then `alembic upgrade head` succeeded cleanly (`f955614f960b` ⇄ `0ac080351a5a`); backend suite re-verified after cycle: **87 passed**
- [x] Playwright upload flow — `e2e/upload-analysis-flow.spec.ts` against local dev servers: **13 passed** (1 backend-gated sub-check skipped internally, no fixture PDF present — documented, not a failure)

---

## Next Phases (not yet started)

| Phase | Description |
|---|---|
| **11** | Dynamic field detection for unrecognized digital PDFs |
| **12** | User accounts and persistent sessions |
| **13** | Administration and content review |

---

## Known Deferred Items

- None currently. All Phase 9 deferred checks were verified above before starting Phase 10.
