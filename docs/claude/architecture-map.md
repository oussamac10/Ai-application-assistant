# Architecture Map

## Backend

- `backend/app/main.py`: FastAPI setup and routes
- `backend/app/core/config.py`: configuration
- `backend/app/database/`: database infrastructure
- `backend/app/forms/`: form definitions and versions
- `backend/app/sessions/`: anonymous sessions and ownership
- `backend/app/questions/`: catalog and answer resolution
- `backend/app/ai/`: Ollama/provider abstractions
- `backend/app/pdf/`: PDF mappings and export
- `backend/app/documents/`: upload, storage, validation, analysis
- `backend/app/commands/`: cleanup commands
- `backend/migrations/`: Alembic migrations
- `backend/tests/`: backend tests

## Frontend

- `frontend/src/app/application/`: application flow
- `frontend/src/features/form-session/`: guided session
- `frontend/src/features/document-upload/`: Phase 9 upload UI
- `frontend/messages/`: en, de, fr, ar
- Check the repository before choosing the Playwright test directory.

## Project

- `fixtures/pdf/`: controlled PDF fixtures
- `docs/decisions/`: ADRs
- `docs/progress/`: archived phase TODOs
- `TODO.md`: current phase only
