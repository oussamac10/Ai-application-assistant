# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Slice 7 of Phase 11: added `FieldDetectionService` (eligibility — rejects supported templates with `supported_template_detected`, requires completed OCR for scanned documents with `ocr_required`/`ocr_not_complete`, idempotent per `source_document_id` + `FIELD_DETECTION_ANALYSIS_VERSION`) and the `POST`/`GET /api/source-documents/{id}/field-detection` routes, wired into `main.py` with full exception-handler mapping. Added `FIELD_DETECTION_PROVIDER`/`FIELD_DETECTION_ANALYSIS_VERSION` settings. 12 new tests (8 service, 4 API), all passing end-to-end against a real Postgres-backed `SourceDocument` (both the `LocalFieldDetectionProvider` and `MockFieldDetectionProvider` are exercised).

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `backend/app/field_detection/service.py`, `repository.py`, `schemas.py`, `api/__init__.py`, `api/routes.py` (new)
- `backend/app/core/config.py` — `FIELD_DETECTION_PROVIDER`/`FIELD_DETECTION_ANALYSIS_VERSION` settings + validator
- `backend/app/main.py` — field-detection router + exception handlers
- `backend/tests/field_detection/test_field_detection_service.py`, `test_field_detection_api.py` (new, 12 tests)
- `TODO.md` — Planned Steps and Acceptance Criteria updated
- `docs/claude/session-handoff.md` — this file

## Checks executed

- `pytest tests/field_detection/` → all field_detection tests passing
- `pytest` (full backend suite) → 190 passed (178 pre-existing + 12 new)
- `ruff check`/`ruff format` → all checks passed, applied, re-verified clean
- `mypy app` → Success: no issues found in 109 source files

## Known limitation carried forward

`LocalFieldDetectionProvider` doesn't yet extract AcroForm choice-widget option values (ComboBox/ListBox), so `select`-type candidates currently have empty `options`. Deferred; worth revisiting before ADR 0010.

## Next action

1. Field review API (`PATCH`/`DELETE /api/source-documents/{id}/field-detection/fields/{field_id}` — confirm/edit/reject).
2. Question-generation bridge (synthetic published `FormTemplate`/`FormVersion`/`FormField` from confirmed fields → existing `SessionService`).
3. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
