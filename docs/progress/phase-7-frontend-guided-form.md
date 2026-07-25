# Project TODO (Archived Phase 7)

## Current Task

Implementing Frontend Guided Form Experience (MVP Phase 7).

## Goal

Build a complete guided frontend experience in Next.js for selecting a form, accepting privacy terms, creating an anonymous session, answering fields one-by-one, handling normalization confirmations and clarifications, editing confirmed answers, displaying progress, reviewing a final summary, and transitioning to a ready-for-export screen.

## Acceptance Criteria

- [x] Phase 6 TODO archived in `docs/progress/phase-6-reusable-question-catalog.md`
- [x] root `TODO.md` reset for Phase 7
- [x] branch is `feature/frontend-guided-form`
- [x] language-selection screen works
- [x] user and output languages remain separate
- [x] Arabic RTL layout works (HTML `dir="rtl"`)
- [x] privacy notice requires explicit acceptance
- [x] anonymous session can be created
- [x] ownership token is stored safely in `sessionStorage`
- [x] ownership token is never placed in URL
- [x] session can be started
- [x] current resolved question is displayed
- [x] one-question-at-a-time flow works
- [x] all 14 supported field types have usable components
- [x] answer submission works
- [x] clarification workflow works
- [x] confirmation workflow works
- [x] previous-field navigation works
- [x] confirmed answer editing works
- [x] progress comes only from backend
- [x] final summary is displayed in order
- [x] final confirmation works
- [x] ready-for-export screen is displayed
- [x] no PDF generation exists
- [x] session reload works in the same browser tab
- [x] missing or expired credentials produce safe restart flow
- [x] provider errors preserve user input
- [x] loading states prevent duplicate actions
- [x] mobile layout works (responsive layout, touch targets)
- [x] keyboard navigation works
- [x] screen-reader labels exist
- [x] raw backend errors and stack traces are not displayed
- [x] frontend tests pass
- [x] Playwright guided-flow tests pass
- [x] backend tests continue to pass
- [x] ESLint passes
- [x] TypeScript checking passes
- [x] Ruff passes for any backend changes
- [x] mypy passes for any backend changes
- [x] documentation is updated
- [x] ADR 0006 is created
- [x] no PDF, OCR, upload, auth, payment, Redis, Celery, object storage, or cloud AI was implemented
- [x] `TODO.md` contains final verification results

## Planned Steps

- [x] Create Git branch `feature/frontend-guided-form`
- [x] Archive Phase 6 TODO in `docs/progress/phase-6-reusable-question-catalog.md`
- [x] Define `PublishedFormResponse` schema and implement `GET /api/published-forms` on the backend
- [x] Install frontend dependencies (`next-intl`, `react-hook-form`, `zod`) and add static locale files in `frontend/messages/`
- [x] Create `LanguageProvider` with client-side localization and Arabic `dir="rtl"` handling
- [x] Implement `sessionCredentials` for storage mapping and `apiClient` mapping HTTP calls
- [x] Build Field Input components for all 14 backend types in `FieldRenderer`
- [x] Implement Landing/Form Selection page (`/application`) with privacy acceptance
- [x] Implement Workflow Session page (`/application/session/[sessionId]`) rendering current resolved question and navigation
- [x] Integrate Clarification sub-form asking for missing inputs and keeping original answer
- [x] Integrate Confirmation sub-form showing proposed normalized values vs original answers
- [x] Implement Summary page (`/application/session/[sessionId]/summary`) displaying all fields
- [x] Implement Ready-for-Export page (`/application/session/[sessionId]/complete`)
- [x] Write Vitest tests for session creation, input components, RTL layouts, and workflows
- [x] Add Playwright E2E tests for the happy path guided flow and key error states
- [x] Run full QA checks, update architecture documentation, and write ADR 0006

## Files Expected to Change

- `TODO.md`
- `backend/app/forms/schemas.py`
- `backend/app/forms/api/routes.py`
- `frontend/package.json`
- `frontend/messages/en.json` (new)
- `frontend/messages/de.json` (new)
- `frontend/messages/fr.json` (new)
- `frontend/messages/ar.json` (new)
- `frontend/src/features/form-session/` (new directories: services, components, types, hooks)
- `frontend/src/app/application/page.tsx` (new)
- `frontend/src/app/application/session/[sessionId]/page.tsx` (new)
- `frontend/src/app/application/session/[sessionId]/summary/page.tsx` (new)
- `frontend/src/app/application/session/[sessionId]/complete/page.tsx` (new)
- `frontend/src/app/page.tsx`
- `frontend/src/test/guided-flow.spec.ts` (new)
- `docs/decisions/0006-frontend-session-state.md` (new)
- `docs/frontend-guided-flow.md` (new)
- `docs/architecture.md`
- `docs/workflow.md`
- `README.md`

## Decisions and Assumptions

- We will keep the session token `ownershipToken` in `sessionStorage` to isolate it by tab and prevent it from appearing in URLs.
- The UI language selection persists across pages and configures the direction `dir` on `html` elements.
- UI state does not override backend data; after every action, the backend response is treated as the single source of truth.
- Playwright tests will run using mock backend data or controlled test fixtures to avoid requiring active LLM/Ollama services.

## Blockers

- None

## Verification

- [x] Backend tests pass: 63 tests passed successfully.
- [x] Frontend tests pass: 13 Vitest unit tests passed successfully.
- [x] Playwright E2E tests pass: `guided-flow.spec.ts` passes successfully in 4.2 seconds against active local/docker instances.
- [x] Linting passes: Next lint (`eslint`) and Python `ruff check` pass with zero warnings or errors.
- [x] Formatting passes: Ruff formatting and prettier formatting checks pass.
- [x] Type checking passes: `tsc --noEmit` and `mypy` check pass without any errors (ignoring migrations folders).
- [x] Acceptance criteria were manually verified.

## Completed

- Created Git branch `feature/frontend-guided-form`
- Archived Phase 6 TODOs in `docs/progress/phase-6-reusable-question-catalog.md`
- Reset root `TODO.md` for Phase 7
- Implemented client-side localization with RTL support
- Implemented secure anonymous session tokens inside `sessionStorage`
- Built premium, accessible field input renderer for all 14 types
- Completed the guided flow with clarification/confirmation loops and back-and-forth editing
- Finalized summary verification and exported completeness screens
- Wrote architecture guides, user-flow diagrams, and ADR 0006
