# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Phase 11 branch and documentation initialized: `feature/dynamic-field-detection` created from `feature/ocr-integration`, `docs/phases/phase-11-dynamic-field-detection.md` written, root `TODO.md` reset for Phase 11 only (Phase 10 remains archived at `docs/progress/phase-10-ocr-integration.md`), and `docs/claude/current-phase.md` updated. No Phase 11 implementation code has been written yet.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this session's work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Working tree otherwise clean except the Phase 11 doc-init changes pending commit

## Files changed

- `docs/phases/phase-11-dynamic-field-detection.md` (new)
- `TODO.md` — reset for Phase 11
- `docs/claude/current-phase.md` — Phase 11 active
- `docs/claude/session-handoff.md` — this file

## Checks executed

None yet — no application code has changed. Full backend/frontend verification (`pytest`, `ruff`, `mypy`, `vitest`, `eslint`, `tsc`, Playwright) was last executed at the end of Phase 10 (109 backend / 41 frontend tests passing) — see `docs/progress/phase-10-ocr-integration.md`.

## Next action

1. Detection domain schemas + `FieldDetectionProvider` protocol (mirrors `app/ocr/providers/base.py`).
2. Deterministic `MockFieldDetectionProvider` with backend tests first (TDD).
3. `FieldDetectionResult`/`DetectedField`/`DetectedFieldOption` models + reversible Alembic migration.
4. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
