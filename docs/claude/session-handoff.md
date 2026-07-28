# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Phase 13 — Automatic Upload-to-Questions User Flow is complete. Starting point was the completed
Phase 12 branch (`feature/user-accounts-persistent-sessions`). This session:

1. Archived Phase 12's TODO to `docs/progress/`, updated the roadmap
   (`docs/claude/project-overview.md`) and `docs/claude/current-phase.md`, reset `TODO.md`, and
   created `feature/automatic-upload-to-questions`.
2. Added deterministic confidence-routing config (`FIELD_AUTO_CONFIRM_THRESHOLD`,
   `FIELD_CLARIFICATION_THRESHOLD`, `FIELD_DETECTION_REVIEW_MODE`) and
   `app/field_detection/confidence.py` — no AI involvement in the routing decision.
3. Wired confidence routing into `FieldDetectionService._candidate_to_model` (in `auto` mode
   only; `manual` mode preserves the exact Phase 11 contract). The existing Phase 11 test suites
   (`test_field_detection_api.py`, `test_question_bridge.py`) now explicitly pin
   `FIELD_DETECTION_REVIEW_MODE="manual"` since they document that specific contract.
4. Extended `question_bridge.create_session_from_confirmed_fields` with
   `include_auto_usable: bool = False` and added `build_review_metadata()`; added
   `FieldDetectionResult.review_metadata` (migration `897a1e1874ae`).
5. Built `app/field_detection/orchestration.py::PrepareQuestionsService` — the single idempotent
   entrypoint (`POST /api/source-documents/{id}/prepare-questions`) composing analyze → OCR (if
   needed) → detect → confidence routing → question generation → session create/reuse.
6. Rebuilt `DocumentUploadForm.tsx`'s post-analysis flow: automatic processing with plain-language
   progress messages, a plain uncertainty screen, and a safe failure screen — no manual
   Detect-Fields/Start-OCR/Start-Guided-Form buttons in the default path. Added
   `features/field-detection/debugMode.ts` to gate a link to the unchanged Phase 11 review screen.
7. Retrofitted 5 existing Phase 9/10/11 Playwright specs whose assertions depended on the removed
   manual UI, and added 2 new spec files.
8. Wrote ADR 0012, `docs/phases/phase-13-automatic-upload-to-questions.md`, and updated
   `docs/architecture.md`, `docs/security.md`, `docs/privacy.md`, `docs/field-detection.md`,
   `docs/user-accounts.md`, `docs/claude/architecture-map.md`, `.env.example`,
   `docker-compose.yml`, `README.md`.
9. Ran full verification — see `TODO.md` "Verification" for exact results, including two real
   bugs found and fixed during this session's own testing (an OCR-ownership-token bug in the new
   orchestration service, and an error-banner visibility regression in the frontend refactor).

## Repository state

- Branch: `feature/automatic-upload-to-questions` (base: `feature/user-accounts-persistent-sessions`)
- Docker Compose `backend`/`frontend` images were rebuilt this session to pick up Phase 13 code;
  both healthy. `docker-compose.yml` gained a passthrough for
  `NEXT_PUBLIC_ENABLE_DETECTION_DEBUG_UI` (default `false`).
- The local Postgres dev database's `basic-registration` fixture was re-seeded
  (`python -m app.commands.load_fixture`) after the backend pytest suite's `TRUNCATE` cleanup
  wiped it — needed for Playwright, same as every prior phase's verification pass.

## Files changed (Phase 13)

Backend: `app/core/config.py`, `app/field_detection/{confidence.py (new), constants.py, service.py,
question_bridge.py, models.py, schemas.py, orchestration.py (new), api/routes.py}`,
`app/sessions/repositories.py`, `backend/migrations/versions/897a1e1874ae_*.py`,
`backend/tests/field_detection/{test_confidence.py (new), test_orchestration.py (new),
test_prepare_questions_api.py (new), test_field_detection_api.py, test_question_bridge.py}`.

Frontend: `src/features/document-upload/components/DocumentUploadForm.tsx`,
`src/features/document-upload/tests/document-upload-automatic-flow.test.tsx` (new),
`src/features/field-detection/{services/apiClient.ts, types/index.ts, debugMode.ts (new)}`,
`messages/{en,de,fr,ar}.json`, `e2e/{dynamic-field-detection-flow.spec.ts, ocr-flow.spec.ts,
upload-analysis-flow.spec.ts, select-manually-translation-flow.spec.ts}` (retrofitted),
`e2e/automatic-upload-to-questions-flow.spec.ts` (new).

Docs: `docs/decisions/0012-automatic-confidence-routing.md` (new),
`docs/phases/phase-13-automatic-upload-to-questions.md` (new), `docs/architecture.md`,
`docs/security.md`, `docs/privacy.md`, `docs/field-detection.md`, `docs/user-accounts.md`,
`docs/claude/{project-overview.md, current-phase.md, architecture-map.md}`, `TODO.md`, `README.md`,
`.env.example`, `docker-compose.yml`, `docs/progress/phase-12-user-accounts-persistent-sessions.md`
(new archive), this file.

## Verification results

See `TODO.md`'s "Verification" section for exact counts: backend 334 passed (312 baseline + 22
new), ruff/mypy clean, migration round-trips cleanly; frontend 81 passed (77 baseline + 4 new),
lint/typecheck clean; Playwright (CI mode, rebuilt Docker, `local`/`ollama` providers) 27 passed,
1 pre-existing failure (`guided-flow.spec.ts`, unrelated to this phase, documented since Phase
9/10).

## Known limitation carried forward

- `guided-flow.spec.ts`'s default-tab mismatch (pre-existing since Phase 9, unrelated to Phase 13).
- One pre-existing Ruff formatting exception under `tests/documents/test_documents.py`.
- Phase 13's own known limitations are listed in `TODO.md` → "Phase 13 Known Limitations" and the
  phase doc's "Known limitations" section (OCR-language default, synchronous orchestration, debug
  route not additionally authenticated, no per-field AI-fallback tracking in review metadata).

## Next action

Phase 13 is done. Recommended next phase: **Phase 14 — Administration and Content Review** (it can
now build directly on `FieldDetectionResult.review_metadata`). Do not start it until explicitly
requested.

## Blockers

None.

## Decisions

See [ADR 0012](../decisions/0012-automatic-confidence-routing.md) for the full architectural
rationale (confidence-routing design, review-mode toggle, orchestration composition, review-
metadata scope, debug-mode gating). Additional decisions are recorded in `TODO.md`'s "Decisions
and Assumptions" section.
