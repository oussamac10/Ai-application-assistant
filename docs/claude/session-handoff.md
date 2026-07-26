# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Slice 5 of Phase 11: added `extraction.py` — `extract_native_document_input` (PyMuPDF: native text word tokens + AcroForm widget name/type/rect/required, PDF point space, rotation-aware) and `extract_ocr_document_input` (builds tokens from an already-completed Phase 10 `OCRResult`, rendered-image pixel space). A document uses exactly one of the two paths, never both — Phase 9/10 eligibility already routes a document to either the digital-unmatched or scanned path, so there's no need to merge coordinate spaces.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `backend/app/field_detection/extraction.py` (new)
- `backend/tests/field_detection/test_extraction.py` (new, 6 tests)
- `TODO.md` — Planned Steps updated
- `docs/claude/session-handoff.md` — this file

## Checks executed

- `pytest tests/field_detection/test_extraction.py` → 6 passed
- `pytest` (full backend suite) → 126 passed (120 pre-existing + 6 new)
- `ruff check app/field_detection tests/field_detection` → all checks passed
- `ruff format` → applied, re-verified clean
- `mypy app` → Success: no issues found in 99 source files

## Next action

1. `LocalFieldDetectionProvider` (rules-based: colon-labels, left/above-label proximity, common patterns, AcroForm passthrough).
2. `service.py` (eligibility, idempotency) + API routes.
3. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
