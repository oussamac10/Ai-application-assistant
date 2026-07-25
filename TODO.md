# Project TODO

## Current Task

Implementing Form Upload and Document Analysis (MVP Phase 9).

## Goal

Implement a secure PDF upload and document-analysis workflow. Users can upload a PDF form, which is validated, stored temporarily, analyzed structurally, and returned with a normalized analysis result (determining PDF characteristics, classification, next-step resolution, and supported template matching).

## Acceptance Criteria

- [x] Phase 8 TODO archived in `docs/progress/phase-8-pdf-template-export.md`
- [x] root `TODO.md` reset for Phase 9
- [x] branch is `feature/form-upload-analysis`
- [ ] upload page supports PDF selection
- [ ] drag-and-drop works
- [ ] privacy acceptance is required
- [ ] only PDF content is accepted
- [ ] file extension is not trusted
- [ ] MIME type is not trusted
- [ ] byte limit is enforced while streaming
- [ ] page limit is enforced
- [ ] empty files are rejected
- [ ] malformed PDFs are rejected safely
- [ ] encrypted PDFs are rejected safely
- [ ] password-protected PDFs are rejected safely
- [ ] dangerous active content is rejected or explicitly flagged
- [ ] source files are stored privately
- [ ] internal storage filenames are generated
- [ ] original filename is sanitized
- [ ] internal storage path is never exposed
- [ ] ownership token is required
- [ ] ownership token is hashed in storage
- [ ] ownership token never appears in a URL
- [ ] document expiration works
- [ ] cleanup removes expired documents
- [ ] cleanup is idempotent
- [ ] page count is analyzed
- [ ] page dimensions are analyzed
- [ ] page rotation is analyzed
- [ ] native text presence is analyzed
- [ ] AcroForm fields are analyzed
- [ ] embedded images are analyzed
- [ ] scanned PDFs are classified
- [ ] digital PDFs are classified
- [ ] fillable PDFs are classified
- [ ] hybrid PDFs are classified
- [ ] unknown PDFs are handled safely
- [ ] predefined template recognition works
- [ ] template recognition is deterministic
- [ ] template recognition is tied to an exact form version
- [ ] duplicate fingerprints are rejected
- [ ] ambiguous matches are rejected
- [ ] supported-template session creation works
- [ ] session creation reuses the existing session service
- [ ] session creation is idempotent
- [ ] unsupported documents do not create sessions
- [ ] analysis returns a normalized next step
- [ ] scanned documents return `ocr_required`
- [ ] digital unsupported documents return `dynamic_field_detection`
- [ ] matched templates return `supported_template`
- [ ] frontend displays upload progress
- [ ] frontend prevents duplicate submissions
- [ ] frontend displays safe errors
- [ ] frontend supports mobile layouts
- [ ] frontend supports keyboard navigation
- [ ] frontend supports screen readers
- [ ] Arabic RTL still works
- [ ] manual form selection still works
- [ ] Phase 7 guided workflow still works
- [ ] Phase 8 export workflow still works
- [ ] backend tests pass
- [ ] frontend tests pass
- [ ] Playwright upload flow passes
- [ ] existing Playwright tests pass
- [ ] migration upgrade succeeds
- [ ] migration downgrade succeeds
- [ ] Ruff linting passes
- [ ] Ruff formatting passes
- [ ] mypy passes
- [ ] ESLint passes
- [ ] TypeScript checking passes
- [ ] documentation is updated
- [ ] ADR 0008 is created
- [ ] no OCR was implemented
- [ ] no arbitrary field detection was implemented
- [ ] no coordinate guessing was implemented
- [ ] no cloud AI was implemented
- [ ] no authentication was implemented
- [ ] no payments were implemented
- [ ] no Redis, Celery, background workers, or object storage were implemented
- [ ] `TODO.md` contains final verification results

## Planned Steps

- [ ] 1. Create Git branch `feature/form-upload-analysis`
- [ ] 2. Update config.py with DOCUMENT_ settings and update `.env.example`
- [ ] 3. Create SourceDocument SQLAlchemy model and generate Alembic migrations for `source_documents` table
- [ ] 4. Create backend `documents` module folder layout and files (`models.py`, `schemas.py`, `errors.py`, `constants.py`, etc.)
- [ ] 5. Implement private storage service, sanitization, and security validations (extension checks, MIME check, PDF header check, page limits, decryption check, active content/javascript check)
- [ ] 6. Implement PDF structural analyzer extracting page count, rotation, dimensions, native text presence, images count, and AcroForm fields
- [ ] 7. Implement predefined template recognition using explicit fingerprints and JSON definition file (e.g. `basic-registration-v1.fingerprint.json`)
- [ ] 8. Implement classifier to determine document type and normalized next step (supported_template, ocr_required, dynamic_field_detection, review_required)
- [ ] 9. Implement upload API endpoints: `POST /api/source-documents` and `GET /api/source-documents/{document_id}` with ownership token security
- [ ] 10. Implement session creation integration endpoint `POST /api/source-documents/{document_id}/session` creating anonymous guided flow sessions from matched templates
- [ ] 11. Extend cleanup CLI command `cleanup_expired_exports` to also clean expired/failed source documents and unlinked temporary files
- [ ] 12. Develop frontend upload feature structure under `src/features/document-upload` (components, services, types, drag-and-drop, upload progress)
- [ ] 13. Update frontend landing page (`application/page.tsx`) to support both manual form selection and form upload/analysis paths
- [ ] 14. Write backend unit tests (tests/documents/), frontend unit tests (Vitest), and Playwright E2E integration tests (including scanned-to-ocr path and digital-to-workflow path)
- [ ] 15. Perform static analyses, linting, verify Alembic migration downgrade/upgrade, and document design decisions in ADR 0008

## Files Expected to Change

- `TODO.md`
- `.env.example`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/commands/cleanup_expired_exports.py`
- `backend/migrations/env.py`
- `frontend/messages/en.json`
- `frontend/messages/de.json`
- `frontend/messages/fr.json`
- `frontend/messages/ar.json`
- `frontend/src/app/application/page.tsx`
- `frontend/src/features/document-upload/` (new files)
- `docs/document-upload-analysis.md` (new)
- `docs/decisions/0008-structural-pdf-document-analysis.md` (new)
- `README.md`
- `docs/architecture.md`
- `docs/workflow.md`
- `docs/testing.md`
- `docs/security.md`
- `docs/privacy.md`
- `docs/frontend-guided-flow.md`
- `docs/pdf-export.md`

## Decisions and Assumptions

- Uploaded source PDF files are stored in a private temporary directory outside the public web root.
- Document ownership is verified via HMAC-SHA256 hash using the custom `X-Document-Token` request header.
- Text marker checks and structural metadata are used for template matching without using vector DBs or AI providers.

## Blockers

- None

## Verification

- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Playwright E2E tests pass
- [ ] Linting passes
- [ ] Formatting passes
- [ ] Type checking passes
- [ ] Acceptance criteria were manually verified
