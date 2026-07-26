# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Slice 2 of Phase 11: added the `field_detection` domain's normalized types and provider protocol (`app/field_detection/providers/base.py` — `BoundingBox`, `DetectionToken`, `AcroFormWidgetInput`, `DetectionPageInput`, `DetectionDocumentInput`, `DetectedFieldCandidate`, `DetectionResult`, `FieldDetectionProvider` Protocol), plus `constants.py`, `errors.py`, and a deterministic `MockFieldDetectionProvider` with TDD-first tests (11 tests, all passing). No persistence, API, or extraction logic yet.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `backend/app/field_detection/__init__.py`, `constants.py`, `errors.py` (new)
- `backend/app/field_detection/providers/__init__.py`, `base.py`, `mock.py` (new)
- `backend/tests/field_detection/test_field_detection_mock_provider.py` (new, 11 tests)
- `TODO.md` — Planned Steps updated
- `docs/claude/session-handoff.md` — this file

## Checks executed

- `pytest tests/field_detection/` → 11 passed
- `pytest` (full backend suite) → 120 passed (109 pre-existing + 11 new)
- `ruff check app/field_detection tests/field_detection` → all checks passed
- `ruff format app/field_detection tests/field_detection` → applied, re-verified clean
- `mypy app` → Success: no issues found in 97 source files

Note: `test_field_detection_mock_provider.py` was deliberately named to avoid a pytest module-collision with the existing `tests/ocr/test_mock_provider.py` (neither `tests/ocr/` nor `tests/field_detection/` has an `__init__.py`, so identical basenames collide under pytest's default import mode).

## Next action

1. `FieldDetectionResult`/`DetectedField`/`DetectedFieldOption` models + reversible Alembic migration (mirrors `app/ocr/models.py`).
2. Native/OCR/AcroForm input normalization (`extraction.py`) using PyMuPDF, independent of the Phase 9 `PDFAnalyzer`.
3. `LocalFieldDetectionProvider` (rules-based).
4. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
