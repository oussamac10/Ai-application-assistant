# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Slice 10 of Phase 11: added the frontend `features/field-detection/` review UI and the Playwright end-to-end flow. `FieldDetectionPanel` shows start/processing/reviewing/failed states, groups candidates by page, allows inline label/type editing, per-field confirm/reject, "confirm all high-confidence" (below `LOW_CONFIDENCE_THRESHOLD = 0.4`, mirroring the backend constant), a low-confidence warning badge, an output-language selector, and a "Create Questions" button (enabled only once ≥1 field is confirmed) that calls the question-generation bridge and redirects into the real guided session. New route `/application/document/[documentId]/detect-fields`. Wired "Detect Fields" buttons into both `DocumentUploadForm` (`dynamic_field_detection` outcome) and `OcrPanel` (after OCR completes), per the two documented user workflows. Full en/de/fr/ar localization (`fieldDetection` namespace + updated `documentUpload`/`documentOcr` keys), RTL-safe (label input uses `dir="auto"`).

Added `frontend/e2e/dynamic-field-detection-flow.spec.ts` — verified against live local dev servers (not just written): upload an unmatched digital PDF (a hand-built minimal-but-valid PDF with real drawn text, since the synthetic single-byte-header PDF used elsewhere doesn't carry enough native text to classify as `digital_pdf`) → Detect Fields → Start Detection → Confirm a field → Create Questions → lands on a real `/application/session/{id}` guided session, with the ownership token never appearing in the URL at any step. Also verified the known-template bypass (no Detect Fields button shown). **Caught and diagnosed a real issue during manual verification**: a stale `docker-compose` `backend`/`frontend` container pair (built before slices 8–9 existed) was still running and shadowing ports 8000/3003, causing PATCH requests to 404 against outdated routes; stopped those containers and re-tested against a freshly started local `uvicorn` — both new e2e tests then passed cleanly. The full local e2e regression suite (`CI=true npx playwright test`) is 17/18 passing — the one failure (`guided-flow.spec.ts`, missing published form fixture) is the same pre-existing, unrelated gap documented since Phase 10.

## Repository state

- Branch: `feature/dynamic-field-detection` (created from `feature/ocr-integration`)
- Two pre-existing uncommitted local dev-config changes carried over from the prior branch, unrelated to this work and intentionally left untouched:
  - `.env.example`: `OCR_PROVIDER` set to `local` (from `mock`)
  - `docker-compose.yml`: backend service now passes through `OCR_PROVIDER: ${OCR_PROVIDER:-local}`
- The stale `docker-compose` `backend`/`frontend` containers were stopped during this session's manual verification (they were outdated anyway) — `postgres` was left running. Whoever resumes work should `docker compose up --build -d` for a fresh image before further Docker-based testing.
- Working tree otherwise clean except this slice's changes pending commit

## Files changed

- `frontend/src/features/field-detection/**` (new: types, apiClient, `FieldDetectionPanel.tsx`)
- `frontend/src/app/application/document/[documentId]/detect-fields/page.tsx` (new)
- `frontend/src/features/document-upload/components/DocumentUploadForm.tsx` — "Detect Fields" button + updated copy
- `frontend/src/features/document-ocr/components/OcrPanel.tsx` — "Detect Fields" button after OCR completes
- `frontend/messages/{en,de,fr,ar}.json` — new `fieldDetection` namespace, updated `documentUpload`/`documentOcr` keys
- `frontend/src/test/field-detection.test.ts` (new, 8 vitest tests)
- `frontend/e2e/dynamic-field-detection-flow.spec.ts` (new, 2 Playwright tests)
- `TODO.md` — Planned Steps and Acceptance Criteria updated
- `docs/claude/session-handoff.md` — this file

## Checks executed

- `npm run typecheck` → clean
- `npm run lint` → no ESLint warnings or errors
- `npm test` (vitest) → 49 passed (41 pre-existing + 8 new)
- `npx playwright test e2e/dynamic-field-detection-flow.spec.ts` (CI=true, live dev servers) → 2 passed
- `npx playwright test` (full suite, CI=true) → 17/18 passed; the 1 failure is the pre-existing `guided-flow.spec.ts` gap, unrelated to this work
- Backend regression re-verified unaffected: `pytest` → 204 passed

## Known limitation carried forward

`LocalFieldDetectionProvider` doesn't yet extract AcroForm choice-widget option values (ComboBox/ListBox), so `select`-type candidates currently have empty `options` and downgrade to a plain `string` question. Deferred; worth revisiting before ADR 0010.

## Next action

1. ADR 0010, `docs/field-detection.md`, and the remaining doc updates (README, architecture.md, workflow.md, testing.md, security.md, privacy.md, document-upload-analysis.md, ocr.md, claude/architecture-map.md).
2. Full verification pass with exact, honest pass/fail counts recorded in `TODO.md`.
3. Do not implement automatic PDF filling/export, or start Phase 12.

## Blockers

None.

## Decisions

- Native-text and AcroForm geometry extraction uses PyMuPDF directly (`extraction.py`), not the Phase 9 `PDFAnalyzer` — the analyzer only counts widgets/text, it doesn't locate them.
- Confirmed detected fields are materialized into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set so the existing `SessionService` and answer/PDF pipeline work completely unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space; every candidate records its coordinate source so the two are never silently mixed.
- Only user-confirmed fields ever generate questions — pending/rejected candidates never do.
- Carried from Phase 10: one guided-flow Playwright test still requires a published Basic Registration v1 form fixture in the local test database (unrelated to OCR or Phase 11); full repository Ruff formatting still has pre-existing issues under `app/documents/`. Neither claim will be reported as passing until actually re-verified.
