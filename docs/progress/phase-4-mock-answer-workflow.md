# Project TODO — Phase 4 Mock Answer Workflow Archived

## Current Task

Implementing mock question and answer workflow using deterministic logic and `MockAIProvider` (MVP Phase 4).

## Goal

Fully functional Q&A workflow including answer model/schema, MockAIProvider, deterministic validations and normalizations, clarification mechanism, field navigation, progress calculations, and final summary/confirmation.

## Acceptance Criteria

- [x] Phase 3 TODO details are archived in `docs/progress/phase-3-form-sessions.md`
- [x] root `TODO.md` contains only the current Phase 4 task and concise history
- [x] work is performed on `feature/mock-answer-workflow`
- [x] answer model and migration exist
- [x] migration upgrade succeeds
- [x] migration downgrade succeeds
- [x] `MockAIProvider` exists
- [x] no external AI calls occur
- [x] current field can be retrieved
- [x] one answer per session and field is enforced
- [x] original answer is preserved
- [x] normalized values are stored
- [x] deterministic validation works
- [x] clarification workflow works
- [x] confirmation workflow works
- [x] confirmed answers can be edited safely
- [x] progress is calculated from confirmed required fields
- [x] previous-field navigation works
- [x] final summary works
- [x] incomplete sessions cannot become ready for export
- [x] complete sessions can transition to ready for export
- [x] session ownership token is required for all endpoints
- [x] sensitive answer data is not logged
- [x] backend tests pass
- [x] existing frontend tests pass
- [x] Ruff linting passes
- [x] Ruff formatting check passes
- [x] mypy passes
- [x] ESLint passes
- [x] TypeScript type checking passes
- [x] documentation is updated
- [x] ADR is created
- [x] no Ollama, cloud AI, OCR, upload, PDF, authentication, or payment functionality was implemented
- [x] `TODO.md` contains final verification results

## Planned Steps

- [x] Create Git branch `feature/mock-answer-workflow`
- [x] Create SQLAlchemy database model for FormAnswer in backend/app/answers/models.py
- [x] Generate and run Alembic migration for the form_answers table
- [x] Implement AIProvider abstraction interface and MockAIProvider class in backend/app/ai/mock_provider.py
- [x] Implement deterministic validators and normalizers for all 14 field types in backend/app/answers/validation/ and app/answers/normalization/
- [x] Create repository for answer database operations in backend/app/answers/repositories.py
- [x] Create Pydantic request/response schemas in backend/app/answers/schemas.py
- [x] Implement main service methods in backend/app/answers/services.py (get current field, previous-field, submit answer, clarify, confirm, edit answer, final summary/confirmation)
- [x] Create FastAPI routes under /api/form-sessions/{session_id}/... for Q&A, navigation, and summaries in backend/app/answers/api/routes.py
- [x] Register new answers router and configure global exception mappings in backend/app/main.py
- [x] Write CLI / database integration and unit tests for Q&A workflows in backend/tests/answers/test_answers.py
- [x] Run quality checks (Ruff, Mypy, ESLint, typecheck) and ensure all backend/frontend tests pass
- [x] Create ADR 0003 and update documentation files (answer-model.md, workflow.md, architecture.md, privacy.md, security.md, testing.md, README.md)

## Files Expected to Change

- `TODO.md`
- `backend/app/main.py`
- `backend/app/answers/models.py`
- `backend/app/answers/repositories.py`
- `backend/app/answers/schemas.py`
- `backend/app/answers/services.py`
- `backend/app/answers/api/routes.py`
- `backend/tests/answers/test_answers.py`
- `docs/answer-model.md`
- `docs/workflow.md`
- `docs/architecture.md`
- `docs/privacy.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/decisions/0003-deterministic-answer-workflow.md`
- `README.md`

## Decisions and Assumptions

- Address validation in Phase 4 is deterministic (e.g. checks dictionary structure, no dynamic AI parsing).
- Navigation back / editing an answer resets that answer's status and recalculates the session's overall completion progress.
- Dependency logic will not be implemented unless explicitly mapped out in fields configuration in a later phase.

## Verification

- [x] Backend tests pass (30/30 passed)
- [x] Frontend tests pass (4/4 passed)
- [x] Linting passes (Next.js ESLint and Ruff clean)
- [x] Formatting passes (Ruff format check clean)
- [x] Type checking passes (Mypy and tsc clean)
- [x] Acceptance criteria were manually verified

## Completed

- Switched to Git branch `feature/mock-answer-workflow`
- Archived Phase 3 TODOs in `docs/progress/phase-3-form-sessions.md`
- Reset root `TODO.md` for Phase 4
- Completed all MVP Phase 4 items and verified quality checks
