# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Slice 8 of Phase 11: added the field review API — `PATCH`/`DELETE /api/source-documents/{id}/field-detection/fields/{field_id}`. `PATCH` allows correcting label, normalized name, field type (validated against `FIELD_TYPES`), required, input bounding box, options, and review status; leaving `reviewStatus` unset auto-transitions a `pending_review` field to `edited` (any other correction counts as having reviewed it), while an explicit `reviewStatus` (e.g. `confirmed`) is honored as-is. `DELETE` marks a candidate `rejected` rather than destroying the row, preserving review history. 8 new tests (3 service, 5 API), all passing.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `backend/app/field_detection/service.py` — `update_field`/`reject_field`/`_resolve_field`
- `backend/app/field_detection/repository.py` — `replace_field_options`
- `backend/app/field_detection/schemas.py` — `DetectedFieldUpdateRequest`, extracted `build_detected_field_schema`
- `backend/app/field_detection/api/routes.py` — PATCH/DELETE routes
- `backend/tests/field_detection/test_field_detection_service.py`, `test_field_detection_api.py` — 14 new tests
- `TODO.md` — Planned Steps and Acceptance Criteria updated
- `docs/claude/session-handoff.md` — this file

## Checks executed

- `pytest tests/field_detection/` → all field_detection tests passing
- `pytest` (full backend suite) → 198 passed (190 pre-existing + 8 new)
- `ruff check`/`ruff format` → all checks passed, applied, re-verified clean
- `mypy app` → Success: no issues found in 109 source files

## Known limitation carried forward

`LocalFieldDetectionProvider` doesn't yet extract AcroForm choice-widget option values (ComboBox/ListBox), so `select`-type candidates currently have empty `options`. Deferred; worth revisiting before ADR 0010.

## Next action

1. Question-generation bridge (synthetic published `FormTemplate`/`FormVersion`/`FormField` from **confirmed** fields only → existing `SessionService`, unmodified).
2. Frontend `features/field-detection/` review UI (en/de/fr/ar, RTL).
3. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
