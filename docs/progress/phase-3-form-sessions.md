# Project TODO — Phase 3 Form Sessions Archived

## Current Task

Implementing secure, temporary, anonymous form sessions connected to one immutable published form version (MVP Phase 3).

## Goal

Create secure, temporary form sessions with opaque public identifiers, ownership token hashes, status workflow transitions, expiration logic, and access controls.

## Acceptance Criteria

- [x] Phase 2 TODO details are archived in `docs/progress/phase-2-form-definitions.md`
- [x] root `TODO.md` contains only the current Phase 3 task and concise history
- [x] work is performed on `feature/form-sessions`
- [x] session model and migration exist
- [x] migration upgrade succeeds
- [x] migration downgrade succeeds
- [x] sessions can only be created for published versions
- [x] raw ownership tokens are never stored
- [x] token is returned only during creation
- [x] session-specific requests require a valid token
- [x] invalid tokens return generic unauthorized responses
- [x] source language is copied from the form version
- [x] output language is validated against the form version
- [x] expiration is calculated by the backend
- [x] expired sessions cannot be modified
- [x] cleanup command works and is idempotent
- [x] status transitions are deterministic
- [x] progress values cannot be controlled by clients
- [x] required API endpoints work
- [x] sensitive values are excluded from responses and logs
- [x] backend tests pass
- [x] existing frontend tests pass
- [x] Ruff linting passes
- [x] Ruff formatting check passes
- [x] mypy passes
- [x] ESLint passes
- [x] TypeScript type checking passes
- [x] documentation is updated
- [x] ADR is created
- [x] no answers, AI, OCR, upload, PDF, or authentication functionality was implemented
- [x] `TODO.md` contains final verification results

## Planned Steps

- [x] Create a new Git branch `feature/form-sessions`
- [x] Create SQLAlchemy database model for FormSession in backend/app/sessions/models.py
- [x] Generate and run Alembic migration for the form_sessions table
- [x] Implement secure cryptographically random token generator and HMAC hashing utilities in backend/app/sessions/security.py
- [x] Create repository for session database operations in backend/app/sessions/repositories.py
- [x] Create Pydantic schemas in backend/app/sessions/schemas.py with camelCase aliases
- [x] Implement session creation and retrieval services with language and token validation in backend/app/sessions/services.py
- [x] Implement transition logic and lifecycle services in backend/app/sessions/validation.py or services
- [x] Create FastAPI routes for creating, starting, and cancelling sessions, plus reading sessions in backend/app/sessions/api/routes.py
- [x] Register new sessions router and configure global exception handlers in backend/app/main.py
- [x] Implement the command line CLI script for cleanup of expired sessions in backend/app/commands/cleanup_expired_sessions.py
- [x] Write backend unit tests for sessions (creation, auth, transitions, expiration, CLI cleanup, API responses) in backend/tests/sessions/test_sessions.py
- [x] Run formatting, linting, type checks, and verify all tests pass
- [x] Write decisions ADR and update documentation (session-model.md, architecture.md, privacy.md, security.md, testing.md, README.md)

## Files Expected to Change

- `TODO.md`
- `backend/app/main.py`
- `backend/pyproject.toml`
- `backend/app/sessions/models.py`
- `backend/app/sessions/repositories.py`
- `backend/app/sessions/schemas.py`
- `backend/app/sessions/services.py`
- `backend/app/sessions/security.py`
- `backend/app/sessions/api/routes.py`
- `backend/app/commands/cleanup_expired_sessions.py`
- `backend/tests/sessions/test_sessions.py`
- `docs/session-model.md`
- `docs/architecture.md`
- `docs/privacy.md`
- `docs/security.md`
- `docs/testing.md`
- `README.md`

## Decisions and Assumptions

- FormSession status transitions will be strictly validated against the allowed matrix:
  - `session_created` -> `in_progress` or `cancelled` or `expired`
  - `in_progress` -> `cancelled` or `expired`
- Inactive/expired/cancelled sessions are terminal and cannot be modified or resumed.
- Ownership token hashes will be stored in PostgreSQL using HMAC SHA-256 with server-side config setting `SESSION_TOKEN_SECRET`.

## Verification

- [x] Backend tests pass (23/23 passed)
- [x] Frontend tests pass (4/4 passed)
- [x] Linting passes (Ruff and Next.js ESLint clean)
- [x] Formatting passes (Ruff format clean)
- [x] Type checking passes (Mypy and tsc clean)
- [x] Acceptance criteria were manually verified
