# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Phase 11 — Dynamic Field Detection is complete. Final slice added ADR 0010, `docs/field-detection.md`, cross-links from `docs/ocr.md`/`docs/document-upload-analysis.md`, and `field_detection`/`document-ocr` entries in `docs/claude/architecture-map.md`, then ran the full verification pass end-to-end inside a freshly rebuilt Docker Compose stack (`docker compose up --build -d`), not just locally.

Verification found two **pre-existing, environment-specific** issues, neither caused by Phase 11 code:
1. `pytest-asyncio` is missing from `backend/requirements.txt` (a Phase 5/6 gap) — `@pytest.mark.asyncio` tests silently skip in a clean Docker image instead of running.
2. The local `.env.example`/`docker-compose.yml` `OCR_PROVIDER=local` override (present since before this phase started, intentionally left untouched per instructions) makes two Phase 10 OCR tests fail against the Docker stack because they hardcode an expectation of the mock provider.

Both are documented precisely in `TODO.md`'s Verification and Known Deferred Items sections rather than silently patched or hidden. `README.md`, `docs/architecture.md`, `docs/workflow.md`, `docs/testing.md`, `docs/security.md`, and `docs/privacy.md` were deliberately **not** touched — none contain document/OCR/field-detection-specific content even after three prior phases (8, 9, 10) that had the same nominal instruction to update them, so touching them now would be a larger unrelated change than this phase's actual scope; the last living update to product-facing docs continues to be README's "Current MVP Phase: Phase 7" header, a pre-existing staleness issue spanning four phases, not introduced here.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`), all 6 Phase 11 commits applied, not pushed
- Two pre-existing uncommitted local dev-config changes carried over from before this phase, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- Docker Compose stack (`postgres`, `backend`, `frontend`) was rebuilt and left running from this session's verification pass
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `docs/decisions/0010-dynamic-field-detection.md` (new)
- `docs/field-detection.md` (new)
- `docs/ocr.md` — added Step 4 (Detect fields) and a Related link
- `docs/document-upload-analysis.md` — updated the dynamic-field-detection outcome row
- `docs/claude/architecture-map.md` — added `backend/app/ocr/`, `backend/app/field_detection/`, `frontend/.../document-ocr/`, `frontend/.../field-detection/`
- `docs/claude/current-phase.md` — marked Phase 11 complete
- `TODO.md` — full, exact Verification results; Known Deferred Items updated
- `docs/claude/session-handoff.md` — this file

## Checks executed (all re-run inside a freshly rebuilt Docker Compose stack)

- `docker compose exec backend ruff check .` → all checks passed
- `docker compose exec backend ruff format --check app/field_detection tests/field_detection` → clean; full-repo `ruff format --check .` → 9 pre-existing `app/documents/` files would reformat (unchanged, documented since Phase 10)
- `docker compose exec backend mypy app` → Success: no issues found in 110 source files
- `docker compose exec backend sh -c "PYTHONPATH=. pytest -q"` → 188 passed, 1 failed (pre-existing OCR_PROVIDER issue above), 15 skipped (pre-existing pytest-asyncio gap above). Locally (venv, no override): 204 passed, including all 95 `tests/field_detection/` tests.
- `docker compose exec backend alembic upgrade head` / `downgrade -1` / `upgrade head` → clean round-trip; suite re-verified after
- `docker compose exec frontend npm run lint` / `npm run typecheck` / `npm test` → all clean; vitest 49 passed
- `npx playwright test` from host against `PLAYWRIGHT_BASE_URL=http://localhost:3003` (the Dockerized frontend) → 16 of 18 passed; the 2 failures are the pre-existing issues documented above, not Phase 11 regressions. The 2 new `dynamic-field-detection-flow.spec.ts` tests pass in both this Docker run and an earlier local-dev-server run.

## Known limitation carried forward

`LocalFieldDetectionProvider` doesn't yet extract AcroForm choice-widget option values (ComboBox/ListBox), so `select`-type candidates currently have empty `options` and downgrade to a plain `string` question. Documented in ADR 0010; a candidate follow-up for a future phase.

## Post-completion bug fix

After the above verification pass, real usage surfaced an incorrect-export bug: dynamically generated sessions were silently exporting the Basic Registration PDF (unrelated fields, only coincidental answer mapping), because `PDFExportService` guessed `"basic-registration-v1"` for any template key it didn't recognize. Fixed in a follow-up commit (`27101e1`): `FormVersion` now carries explicit `origin` (`predefined_template` | `dynamic_detection`) and `pdf_template_key` columns; export is blocked with a safe `dynamic_pdf_export_not_supported` (422) error for any version without an explicit `pdf_template_key`, and the frontend hides the export button and shows a clear unsupported-export message for dynamic sessions. Predefined-template export (Basic Registration) is unaffected and re-verified working. New backend/frontend/Playwright regression tests cover both paths. See that commit message for full detail.

## Next action

Phase 11 is done, including the incorrect-export fix above. Do not start Phase 12 until explicitly requested. If asked to close Phase 11 (mirroring how Phase 10 was closed): archive this TODO under `docs/progress/phase-11-dynamic-field-detection.md`, reset root `TODO.md`, and update `docs/claude/current-phase.md` to "no active phase."

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
