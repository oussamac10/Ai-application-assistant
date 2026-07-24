# Project TODO

## Current Task

Implementing multilingual, versioned form definitions in the backend (MVP Phase 2).

## Goal

Fully functional form templates, versions (editable drafts, immutable published, archived), deterministic configuration validation, cloning, REST endpoints, CLI fixture loader, migrations, and backend tests.

## Acceptance Criteria

- [ ] Phase 1 TODO details are archived in `docs/progress/phase-1-foundation.md`
- [ ] root `TODO.md` contains only the current Phase 2 task and concise history
- [ ] work is performed on `feature/form-definitions`
- [ ] all required models exist
- [ ] database constraints are implemented
- [ ] Alembic upgrade succeeds
- [ ] Alembic downgrade succeeds
- [ ] templates can be created, listed, and read
- [ ] draft versions can be created
- [ ] fields can be added to drafts
- [ ] fields are returned in deterministic order
- [ ] translated labels are stored separately
- [ ] choice options use canonical values
- [ ] field configurations are validated deterministically
- [ ] published versions cannot be modified
- [ ] archived versions cannot be modified
- [ ] versions can be cloned into independent drafts
- [ ] publication validation works
- [ ] required API endpoints work
- [ ] fictional development fixture exists
- [ ] backend tests pass
- [ ] existing frontend tests pass
- [ ] Ruff linting passes
- [ ] Ruff formatting check passes
- [ ] mypy passes
- [ ] ESLint passes
- [ ] TypeScript type checking passes
- [ ] documentation is updated
- [ ] ADR is created
- [ ] no session, answer, AI, OCR, upload, or PDF functionality was implemented
- [ ] `TODO.md` contains final verification results

## Planned Steps

- [x] Create SQLAlchemy database models for FormTemplate, FormVersion, FormField, FormFieldTranslation, FormFieldOption, FormFieldOptionTranslation
- [x] Generate and run Alembic migration for the form tables
- [x] Implement configuration validations for all field types (String, Person Name, Integer, Decimal, Money, Date, Choices)
- [x] Implement database repositories for database operations on templates and versions
- [x] Create Pydantic schemas for requests and responses
- [x] Implement draft field creation and patch modification services (protecting published/archived versions)
- [x] Implement version publishing validation service and status updates
- [x] Implement draft cloning business logic service (creating independent copies)
- [x] Create API routes for template, version, field, publish, and clone endpoints
- [x] Register API routes in backend/app/main.py
- [x] Write CLI command to load the "Basic Registration" development fixture
- [x] Add backend unit tests for templates, versions, fields, cloning, publishing, and error states
- [x] Verify formatting, linting, type-checking, and tests pass successfully
- [x] Update README.md and documentation (form-model.md, architecture.md, decisions ADR)

## Files Expected to Change

- `TODO.md`
- `backend/app/main.py`
- `backend/app/forms/models.py`
- `backend/app/forms/repositories.py`
- `backend/app/forms/schemas.py`
- `backend/app/forms/services.py`
- `backend/app/forms/validation/config_validation.py`
- `backend/app/forms/api/routes.py`
- `backend/app/commands/load_fixture.py`
- `backend/tests/forms/test_forms.py`
- `docs/form-model.md`
- `docs/architecture.md`
- `docs/decisions/0001-immutable-form-versions.md`
- `README.md`

## Decisions and Assumptions

- Deleting a template does not delete versions automatically (no DB-level CASCADE from Template to Version to prevent silent loss of published history).
- Pydantic v2 schemas will use alias generator or custom fields for JSON API compatibility if needed, mapping camelCase from client to snake_case.
- Python 3.12 virtual environment is activated for test execution.

## Blockers

- None

## Verification

- [x] Backend tests pass (16/16 passed)
- [x] Frontend tests pass (4/4 passed)
- [x] Linting passes (Ruff and ESLint clean)
- [x] Formatting passes (Ruff clean)
- [x] Type checking passes (Mypy and tsc clean)
- [x] Acceptance criteria were manually verified (Basic Registration fixture loaded and verified)

## Completed

- Switched to Git branch `feature/form-definitions`
- Archived Phase 1 TODOs in `docs/progress/phase-1-foundation.md`
- Reset root `TODO.md` for Phase 2
- Implemented all Phase 2 requirements (database models, repository, business logic, endpoints, fixture loader, backend unit tests, architecture docs, ADR)
