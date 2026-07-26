# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Slice 3 of Phase 11: added `FieldDetectionResult`/`DetectedField`/`DetectedFieldOption` SQLAlchemy models and a reversible Alembic migration. One active result per `(source_document_id, analysis_version)`; `DetectedField` rows carry label/input bounding boxes as JSON and a `review_status` (`pending_review|confirmed|edited|rejected`); `DetectedFieldOption` covers radio/select candidates. Migration verified upgrade → downgrade → upgrade against real Postgres.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `backend/app/field_detection/models.py` (new)
- `backend/migrations/env.py` — registered the three new models
- `backend/migrations/versions/87c29a7b8958_*.py` (new)
- `TODO.md` — Planned Steps updated
- `docs/claude/session-handoff.md` — this file

## Checks executed

- `alembic upgrade head` / `downgrade -1` / `upgrade head` → clean round-trip against real Postgres
- `pytest` (full backend suite) → 120 passed, re-verified after the migration cycle
- `ruff check app/field_detection migrations/env.py` → all checks passed
- `ruff format` → applied, re-verified clean
- `mypy app` → Success: no issues found in 98 source files

## Next action

1. Native/OCR/AcroForm input normalization (`extraction.py`) using PyMuPDF, independent of the Phase 9 `PDFAnalyzer`.
2. `LocalFieldDetectionProvider` (rules-based).
3. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
