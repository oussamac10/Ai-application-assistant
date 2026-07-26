# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Slice 9 of Phase 11: added the question-generation bridge (`app/field_detection/question_bridge.py`). Confirmed `DetectedField` rows are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set — reusing `FormService`'s own validation (choice fields need options, labels required for the source language, ...) rather than reimplementing it — then the existing, unmodified `SessionService.create_session` starts a real guided session. New `POST /api/source-documents/{id}/field-detection/session` endpoint. Only fields with `review_status == "confirmed"` are ever used; pending/rejected candidates never generate a question. 6 new tests (4 bridge, 2 API), all passing.

`DetectedField.field_type` → form-model `field_type` mapping: `text→string`, `multiline_text→multiline_text`, `date→date`, `email→email`, `phone→phone`, `address→address`, `number→integer`, `currency→money`, `checkbox→boolean`, `radio→single_choice`, `select→single_choice` (downgraded to `string` if no options — matches the known AcroForm-choice-options limitation), `signature→string`, `unknown→string`.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `backend/app/field_detection/question_bridge.py` (new)
- `backend/app/field_detection/service.py` — `create_session_from_confirmed_fields`
- `backend/app/field_detection/api/routes.py` — `POST .../field-detection/session`
- `backend/tests/field_detection/test_question_bridge.py` (new, 4 tests)
- `backend/tests/field_detection/test_field_detection_api.py` — 2 new tests, `clean_db` now also truncates `form_templates`/`form_sessions`
- `TODO.md` — Planned Steps and Acceptance Criteria updated
- `docs/claude/session-handoff.md` — this file

## Checks executed

- `pytest tests/field_detection/` → all field_detection tests passing (95)
- `pytest` (full backend suite) → 204 passed (198 pre-existing + 6 new)
- `ruff check`/`ruff format` → all checks passed, applied, re-verified clean
- `mypy app` → Success: no issues found in 110 source files

## Known limitation carried forward

`LocalFieldDetectionProvider` doesn't yet extract AcroForm choice-widget option values (ComboBox/ListBox), so `select`-type candidates currently have empty `options` and downgrade to a plain `string` question. Deferred; worth revisiting before ADR 0010.

## Next action

1. Frontend `features/field-detection/` review UI (en/de/fr/ar, RTL) — candidate list, confirm/edit/reject, "Create questions" button.
2. Playwright `dynamic-field-detection-flow.spec.ts`.
3. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
