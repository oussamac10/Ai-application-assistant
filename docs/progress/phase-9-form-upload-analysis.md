# Project TODO Archive - Phase 9: Form Upload and Document Analysis

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

**No active task.** Phase 9 is complete and pushed.

---

## Phase 9 — Final Verification Results

### Acceptance criteria

- [x] Phase 8 archived in `docs/progress/phase-8-pdf-template-export.md`
- [x] branch is `feature/form-upload-analysis`
- [x] upload page supports PDF selection
- [x] drag-and-drop works
- [x] privacy acceptance is required
- [x] only PDF content is accepted
- [x] file extension is not trusted (backend validates %PDF header)
- [x] MIME type is not trusted (backend validates content)
- [x] byte limit is enforced (10 MB, configurable via `DOCUMENT_UPLOAD_MAX_BYTES`)
- [x] page limit is enforced (20 pages, configurable via `DOCUMENT_UPLOAD_MAX_PAGES`)
- [x] empty files are rejected
- [x] malformed PDFs are rejected safely
- [x] encrypted PDFs are rejected safely (`encrypted_pdf` error code)
- [x] password-protected PDFs are rejected safely (`password_protected_pdf` error code)
- [x] dangerous active content is rejected (JS, OpenAction, AA, Launch, embedded files)
- [x] source files are stored privately (UUID-based path under `DOCUMENT_STORAGE_PATH`)
- [x] internal storage filenames are generated (random UUID)
- [x] original filename is sanitized before storage
- [x] internal storage path is never exposed in API responses
- [x] ownership token is required for GET and session creation
- [x] ownership token is hashed in storage (HMAC-SHA256, same pattern as sessions)
- [x] ownership token never appears in a URL
- [x] document expiration is set at upload time (`DOCUMENT_EXPIRATION_HOURS`, default 24h)
- [x] cleanup removes expired documents from disk and sets status to `deleted`
- [x] cleanup is idempotent
- [x] page count is analyzed
- [x] page dimensions are analyzed (per page, with ±5pt tolerance for fingerprinting)
- [x] page rotation is analyzed
- [x] native text presence is analyzed (character count heuristic)
- [x] AcroForm fields are analyzed (Widget annotation count + field names)
- [x] embedded images are analyzed (XObject Image detection)
- [x] scanned PDFs are classified (`scanned_pdf`)
- [x] digital PDFs are classified (`digital_pdf`)
- [x] fillable PDFs are classified (`fillable_pdf`)
- [x] hybrid PDFs are classified (`hybrid_pdf`)
- [x] unknown PDFs are handled safely (`unknown`)
- [x] predefined template recognition works (fingerprint JSON files in `fixtures/pdf/`)
- [x] template recognition is deterministic
- [x] template recognition is tied to an exact form version
- [x] ambiguous matches are rejected (multiple fingerprint matches → no template)
- [x] supported-template session creation works
- [x] session creation reuses the existing `SessionService`
- [x] unsupported documents do not create sessions
- [x] analysis returns a normalized next step
- [x] scanned documents return `ocr_required`
- [x] digital unsupported documents return `dynamic_field_detection`
- [x] matched templates return `supported_template`
- [x] frontend displays upload progress (XHR progress events)
- [x] frontend prevents duplicate submissions (disabled state during upload)
- [x] frontend displays safe errors (per error code, not raw server messages)
- [x] Arabic RTL still works
- [x] manual form selection still works (tab switcher)
- [x] Phase 7 guided workflow still works (72 backend tests passing)
- [x] Phase 8 export workflow still works (72 backend tests passing)
- [x] backend tests pass — **72 passed, 15 skipped**
- [x] frontend unit tests pass — **22 passed (Vitest)**
- [x] Playwright upload E2E spec committed (`e2e/upload-analysis-flow.spec.ts`)
- [x] Ruff linting passes — all checks passed
- [x] TypeScript checking passes — zero errors (`tsc --noEmit`)
- [x] documentation updated — ADR 0008, user guide
- [x] ADR 0008 created (`docs/decisions/0008-structural-pdf-document-analysis.md`)
- [x] no OCR was implemented (Phase 10)
- [x] no arbitrary field detection was implemented (Phase 11)
- [x] no coordinate guessing was implemented
- [x] no cloud AI was implemented
- [x] no authentication was implemented
- [x] no payments were implemented
- [x] no Redis, Celery, background workers, or object storage were implemented

---

## Next Phases (not yet started)

| Phase | Description |
|---|---|
| **10** | OCR for scanned PDFs (`MockOCRProvider` → `PyMuPDFTextProvider` → future cloud OCR) |
| **11** | Dynamic field detection for unrecognized digital PDFs |
| **12** | User accounts and persistent sessions |
| **13** | Payment processing |

---

## Known Deferred Items

- Playwright E2E upload tests require a running frontend + backend (`npm run dev`). The spec is committed and runs in CI with `CI=true`. Backend-gated test is skipped locally.
- `mypy` type check not yet run (deferred; Python 3.11 type annotations are used throughout and ruff+tsc covers most issues).
- Alembic migration downgrade path not manually verified (upgrade is verified via `docker compose exec backend alembic upgrade head`).
