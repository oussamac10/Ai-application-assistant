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

---

## Current Task

**Phase 11 — Dynamic Field Detection.** Branch: `feature/dynamic-field-detection`. Base: `feature/ocr-integration`. **Status: Implementation complete, full verification pass done.**

## Goal

Analyze unrecognized uploaded forms (unmatched digital PDFs and OCR-processed scanned PDFs) and detect candidate form fields from native PDF text/coordinates, OCR text/lines/words/coordinates/confidence, and AcroForm widget metadata. Produce a normalized, persisted, user-reviewable field-detection result. Generate questions from confirmed fields only, via the existing guided-session workflow. Do not automatically fill arbitrary PDFs.

See `docs/phases/phase-11-dynamic-field-detection.md` for the full specification.

## Acceptance Criteria

- [x] `FieldDetectionProvider` protocol
- [x] deterministic `MockFieldDetectionProvider`
- [x] rules-based `LocalFieldDetectionProvider`
- [x] native PDF text + coordinate extraction (PyMuPDF)
- [x] AcroForm widget metadata extraction (name, type, rect, page)
- [x] OCR-result consumption as a detection input source
- [x] label detection and label/input-area association
- [x] field-type classification with deterministic ordering and confidence
- [x] persisted `FieldDetectionResult`/`DetectedField`/`DetectedFieldOption` + reversible migration
- [x] ownership + expiration checks reused from Phase 9
- [x] idempotent detection API (`POST`/`GET /api/source-documents/{id}/field-detection`)
- [x] field review API (confirm/edit/reject)
- [x] question generation from confirmed fields only, via existing guided workflow
- [x] frontend review UI, all 4 languages, RTL preserved
- [x] backend, frontend, migration, and Playwright tests
- [x] ADR 0010, `docs/field-detection.md`, updated docs
- [x] Ruff, mypy, ESLint, TypeScript all pass
- [x] Phase 7, 8, 9, 10 regressions preserved (see Verification section for the two pre-existing, environment-specific exceptions)

## Planned Steps

- [x] Phase initialization and documentation
- [x] Detection domain schemas and provider protocol
- [x] Deterministic mock provider
- [x] Persistence and reversible migration
- [x] Native/OCR/AcroForm input normalization (extraction.py)
- [x] Local heuristic provider
- [x] Service, eligibility, idempotency, and API
- [x] Field review API
- [x] Question-generation bridge
- [x] Frontend review UI
- [x] Playwright tests
- [x] Documentation and full verification

## Files Expected to Change

See `docs/phases/phase-11-dynamic-field-detection.md` "Files Expected to Change" — initial estimate, may be updated during implementation.

## Decisions and Assumptions

- Native-text and AcroForm geometry extraction uses PyMuPDF, independent of the Phase 9 `PDFAnalyzer` (which only counts, doesn't locate).
- Confirmed fields become a real, temporary, published `FormVersion` so the entire existing session/answer/PDF pipeline works unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space — never silently mixed.
- Supported languages for generated questions remain en/de/fr/ar.

## Blockers

- None

## Verification

All checks below were run twice: once locally (venv/npm) and once inside the
Docker Compose stack (`docker compose up --build -d`, then `docker compose
exec backend|frontend ...`), per the completion checklist. Results are from
the Docker run except where noted.

- [x] Backend tests pass — `pytest` → **188 passed, 1 failed, 15 skipped**
  - The 1 failure (`tests/ocr/test_ocr_api.py::test_api_ocr_flow`) is caused by the pre-existing, intentionally-untouched local `.env.example`/`docker-compose.yml` override (`OCR_PROVIDER=local`) making a Phase 10 test that hardcodes `provider == "mock"` fail when run against real Tesseract instead of the mock provider. Not a Phase 11 regression; passes locally where that override isn't set.
  - The 15 skipped are pre-existing `@pytest.mark.asyncio` tests (Phase 5/6 `ai`/`questions` modules) silently skipped because `pytest-asyncio` is missing from `backend/requirements.txt` — a pre-existing dependency-tracking gap discovered during this Docker verification, not introduced by Phase 11 and out of this phase's scope to fix.
  - Locally (venv, no OCR_PROVIDER override, pytest-asyncio installed ad hoc): **204 passed**, all Phase 11 tests included (95 in `tests/field_detection/`)
- [x] Frontend tests pass — `npm test` (vitest, in Docker) → **49 passed** (41 pre-existing + 8 new)
- [x] Playwright Phase 11 flows pass — `e2e/dynamic-field-detection-flow.spec.ts` against the Docker Compose stack: **2 passed**
- [ ] Full Playwright regression suite passes — **16 of 18 passed** against the Docker Compose stack
  - `guided-flow.spec.ts` fails: same pre-existing missing-published-form-fixture gap documented since Phase 10
  - `ocr-flow.spec.ts` (`upload scanned PDF shows OCR-required state`) fails: same `OCR_PROVIDER=local` cause as the pytest failure above — the test expects mock-provider output text
  - Neither failure is caused by Phase 11 code
- [x] Ruff lint passes — `ruff check .` (in Docker) → all checks passed
- [x] Phase 11 new/modified files pass Ruff formatting — `ruff format --check app/field_detection tests/field_detection` → all clean
- [ ] Full backend repository formatting check
  - `ruff format --check .` → 9 files would be reformatted, all under `app/documents/` (+its test file) — the same pre-existing gap documented since Phase 10, intentionally left unchanged
- [x] mypy passes — `mypy app` → **Success: no issues found in 110 source files**
- [x] ESLint passes — `npm run lint` → no warnings or errors
- [x] TypeScript passes — `npm run typecheck` → clean
- [x] Migration downgrade and re-upgrade pass — `alembic downgrade -1` / `upgrade head` round-tripped cleanly against the Docker Postgres; suite re-verified after
- [x] Acceptance criteria manually verified — full flow driven through a live browser via Playwright against both a local dev server and the Docker Compose stack: upload → detect fields → confirm/reject → create questions → real guided session, ownership token never in the URL; known-template bypass confirmed

---

## Next Phases (not yet started)

| Phase | Description |
|---|---|
| **12** | User accounts and persistent sessions |
| **13** | Administration and content review |

---

## Known Deferred Items

Carried from Phase 10:

- One guided-flow test requires a published Basic Registration v1 form fixture seeded in the local test database; unrelated to OCR or Phase 11
- Full repository Ruff formatting still includes pre-existing formatting issues under `app/documents/`, predating Phase 10 and intentionally left unchanged

Found during Phase 11's Docker verification pass:

- `pytest-asyncio` is missing from `backend/requirements.txt`, so `@pytest.mark.asyncio` tests in `tests/ai/` and `tests/questions/` are silently skipped (not failed) when the backend runs from a clean Docker image. They pass locally because a venv already had the package installed ad hoc. Pre-existing gap from Phases 5/6, out of Phase 11's scope to fix, but should be addressed before relying on Docker-based CI for those modules.
- The local `.env.example`/`docker-compose.yml` `OCR_PROVIDER=local` override (present before Phase 11 started, intentionally left untouched per instructions) makes one Phase 10 test (`tests/ocr/test_ocr_api.py::test_api_ocr_flow`) and one Phase 10 Playwright test (`ocr-flow.spec.ts`) fail when run against the Docker Compose stack, since both hardcode an expectation of the mock OCR provider. Not a Phase 11 regression; resolved by resetting `OCR_PROVIDER` to `mock` for automated runs.
- Both the `pytest-asyncio` gap and the `OCR_PROVIDER` override are environment/dependency issues uncovered by testing in Docker specifically, not code defects introduced by Phase 11.

## Post-completion fix

Real usage after this verification pass surfaced an incorrect-export bug: dynamically generated sessions were silently exporting the Basic Registration PDF instead of being blocked. Fixed (commit `27101e1`) by adding explicit `origin`/`pdf_template_key` to `FormVersion` and a `dynamic_pdf_export_not_supported` (422) guard in `PDFExportService`; dynamic sessions can no longer export any PDF, predefined-template export is unaffected. See `docs/claude/session-handoff.md` for detail and new regression tests.
