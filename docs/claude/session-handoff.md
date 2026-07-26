# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Slice 6 of Phase 11: added the `LocalFieldDetectionProvider` and its supporting modules — `geometry.py` (line clustering, left-of/above proximity), `labeling.py` (colon-terminated label lines, nearest-label lookup for an input area), `classification.py` (keyword-based label→field_type guesses plus email/phone/currency value-pattern matching), and `normalization.py` (safe field names, low-confidence→`unknown` downgrade, dedup by normalized name, deterministic page/position ordering). AcroForm widgets are authoritative when present (label found via proximity, "text" widgets refined by label wording); otherwise colon-terminated lines drive detection. 52 new tests across geometry/classification/normalization/local-provider, all passing.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `backend/app/field_detection/geometry.py`, `labeling.py`, `classification.py`, `normalization.py`, `providers/local.py` (new)
- `backend/tests/field_detection/test_geometry.py`, `test_classification.py`, `test_normalization.py`, `test_local_provider.py` (new, 52 tests)
- `TODO.md` — Planned Steps and Acceptance Criteria updated
- `docs/claude/session-handoff.md` — this file

## Checks executed

- `pytest tests/field_detection/` → all field_detection tests passing
- `pytest` (full backend suite) → 178 passed (126 pre-existing + 52 new)
- `ruff check app/field_detection tests/field_detection` → all checks passed
- `ruff format` → applied, re-verified clean
- `mypy app` → Success: no issues found in 104 source files

## Known limitation carried forward

`LocalFieldDetectionProvider` doesn't yet extract AcroForm choice-widget option values (ComboBox/ListBox), so `select`-type candidates currently have empty `options`. `extraction.py`'s `AcroFormWidgetInput` would need a `choices` field to support this — deferred rather than reopening slice 5 mid-slice-6; worth revisiting before ADR 0010 if choice fields turn out to be common in test documents.

## Next action

1. `service.py` (eligibility reusing Phase 9/10, idempotency per document+analysis_version) + API routes (`POST`/`GET /api/source-documents/{id}/field-detection`).
2. Field review API (`PATCH`/`DELETE .../fields/{field_id}`).
3. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
