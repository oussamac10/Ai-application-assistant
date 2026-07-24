# Project TODO — Phase 2 Form Definitions Archived

## Current Task

Implementing multilingual, versioned form definitions in the backend (MVP Phase 2).

## Goal

Fully functional form templates, versions (editable drafts, immutable published, archived), deterministic configuration validation, cloning, REST endpoints, CLI fixture loader, migrations, and backend tests.

## Acceptance Criteria

- [x] Phase 1 TODO details are archived in `docs/progress/phase-1-foundation.md`
- [x] root `TODO.md` contains only the current Phase 2 task and concise history
- [x] work is performed on `feature/form-definitions`
- [x] all required models exist
- [x] database constraints are implemented
- [x] Alembic upgrade succeeds
- [x] Alembic downgrade succeeds
- [x] templates can be created, listed, and read
- [x] draft versions can be created
- [x] fields can be added to drafts
- [x] fields are returned in deterministic order
- [x] translated labels are stored separately
- [x] choice options use canonical values
- [x] field configurations are validated deterministically
- [x] published versions cannot be modified
- [x] archived versions cannot be modified
- [x] versions can be cloned into independent drafts
- [x] publication validation works
- [x] required API endpoints work
- [x] fictional development fixture exists
- [x] backend tests pass
- [x] existing frontend tests pass
- [x] Ruff linting passes
- [x] Ruff formatting check passes
- [x] mypy passes
- [x] ESLint passes
- [x] TypeScript type checking passes
- [x] documentation is updated
- [x] ADR is created
- [x] no session, answer, AI, OCR, upload, or PDF functionality was implemented
- [x] `TODO.md` contains final verification results

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
