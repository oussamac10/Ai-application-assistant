# Project TODO Archive - Phase 8: PDF Template Mapping and Export

## Current Task

Implementing PDF Template Mapping and Export (MVP Phase 8).

## Goal

Implement secure PDF generation for one predefined form template using explicit field mappings, validation, idempotency, temporary storage, and a secure download flow.

## Acceptance Criteria

- [x] Phase 7 TODO archived in `docs/progress/phase-7-frontend-guided-form.md`
- [x] root `TODO.md` reset for Phase 8
- [x] branch is `feature/pdf-template-export`
- [x] one predefined PDF template exists
- [x] explicit mapping file exists
- [x] mapping is tied to an exact form version
- [x] no coordinates are guessed
- [x] `FormExport` model exists
- [x] migration upgrade succeeds
- [x] migration downgrade succeeds
- [x] only ready-for-export sessions can export
- [x] ownership token is required for export creation
- [x] ownership token is required for download
- [x] confirmed values are used
- [x] deterministic formatting works
- [x] overflow policy is enforced
- [x] generated PDF is validated
- [x] generation is idempotent
- [x] repeated requests do not create duplicate exports
- [x] temporary storage is private
- [x] export records have expiration
- [x] cleanup command works
- [x] download endpoint streams PDF securely
- [x] internal storage path is never exposed
- [x] frontend can generate and download PDF
- [x] frontend download sends ownership token in header
- [x] ownership token never appears in URL
- [x] generated PDFs contain no unintended fixture data
- [x] backend tests pass
- [x] frontend tests pass
- [x] Playwright export flow passes
- [x] Ruff linting passes
- [x] Ruff formatting passes
- [x] mypy passes
- [x] ESLint passes
- [x] TypeScript checking passes
- [x] documentation is updated
- [x] ADR 0007 is created
- [x] no arbitrary uploads, OCR, auth, payment, Redis, Celery, object storage, or cloud AI was implemented
- [x] `TODO.md` contains final verification results

## Planned Steps

- [x] 1. Create Git branch `feature/pdf-template-export`
- [x] 2. Add PDF python dependencies (`pypdf`, `reportlab`) to `requirements.txt` and install them
- [x] 3. Create script to generate a base pre-defined PDF template with AcroForm fields (e.g. `fixtures/pdf/basic-registration-v1.pdf`) and save the explicit JSON mapping `basic-registration-v1.mapping.json`
- [x] 4. Define `FormExport` SQLAlchemy model and generate Alembic migrations for `form_exports` table
- [x] 5. Implement registry/loader to resolve PDF template key, mapping version, and reject invalid/duplicate mappings
- [x] 6. Create `PDFRenderer` using `pypdf` to fill AcroForm fields from confirmed canonical data
- [x] 7. Implement formatting rules (dates, booleans, country, choices, structured address)
- [x] 8. Implement overflow policies (reject, truncate, wrap) and validate generated files (file size, PDF signature, checksum)
- [x] 9. Build `PDFExportService` enforcing session status constraints, ownership checks, and idempotency
- [x] 10. Build exports API endpoints: `POST /api/form-sessions/{session_id}/exports` and `GET /api/form-exports/{export_id}/download` with ownership checks
- [x] 11. Implement cleanup CLI command `python -m app.commands.cleanup_expired_exports` to delete expired temporary files and update statuses
- [x] 12. Integrate frontend download button on complete page fetching PDF as Blob using custom session token header and revoking URL afterwards
- [x] 13. Write comprehensive unit and integration tests (mapping validation, export eligibility, formatting, overflow, idempotency, download authorization)
- [x] 14. Add Playwright E2E tests for the PDF generation and download flow
- [x] 15. Perform QA checks, verify manual rendering of Arabic/non-Latin characters, update all documentations, and write ADR 0007

## Files Expected to Change

- `TODO.md`
- `backend/requirements.txt`
- `backend/app/pdf/` (new module directory: mappings, renderers, schemas, services, models, repositories, validation, api)
- `backend/app/main.py` (register routes and exception handlers)
- `backend/app/core/config.py` (register PDF settings)
- `backend/migrations/env.py` (register FormExport metadata)
- `frontend/messages/en.json` (add PDF strings)
- `frontend/messages/de.json`
- `frontend/messages/fr.json`
- `frontend/messages/ar.json`
- `frontend/src/app/application/session/[sessionId]/complete/page.tsx`
- `frontend/src/features/form-session/services/apiClient.ts`
- `docs/pdf-export.md` (new)
- `docs/decisions/0007-explicit-pdf-template-mapping.md` (new)
- `docs/architecture.md`
- `docs/workflow.md`
- `docs/testing.md`
- `docs/privacy.md`
- `docs/security.md`
- `docs/frontend-guided-flow.md`
- `README.md`
- `docs/progress/phase-7-frontend-guided-form.md`

## Decisions and Assumptions

- We will fill the predefined PDF form using standard AcroForm PDF field names (`pypdf` strategy) to keep layout logic clean and simple.
- Temporary files will be deleted by a cron job or manual cleanup command, expiring after 24 hours.
- Access to the download endpoint requires verifying the session token ownership matching the session ID.

## Blockers

- None

## Verification

- [x] Backend tests pass (59 passed, 15 skipped)
- [x] Frontend tests pass (13 passed)
- [x] Playwright E2E tests pass (1 passed)
- [x] Linting passes (ruff check and next lint are clean)
- [x] Formatting passes (ruff format is clean)
- [x] Type checking passes (mypy and tsc are clean)
- [x] Acceptance criteria were manually verified

## Completed

- Archived Phase 7 TODOs in `docs/progress/phase-7-frontend-guided-form.md`
- Reset root `TODO.md` for Phase 8
- Fully implemented Phase 8 PDF template mapping and secure export flow
