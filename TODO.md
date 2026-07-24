# Project TODO

## Current Task

Implementing a Reusable Question Catalog and Hybrid Resolution System (MVP Phase 6).

## Goal

Decouple form questions from specific form versions by introducing a reusable question catalog with stable semantic keys. Resolve questions through a hybrid lookup pipeline (database approved first, static translation fallback, AI translation/generation as pending review, deterministic fallback as last resort) while ensuring no duplicate AI calls.

## Acceptance Criteria

- [x] Phase 5 TODO details are archived in `docs/progress/phase-5-local-ollama-provider.md`
- [x] root `TODO.md` reset for Phase 6
- [x] branch is `feature/reusable-question-catalog`
- [x] `QuestionDefinition` model exists
- [x] `QuestionTranslation` model exists
- [x] question resolution metadata is recorded (resolution log/audit model)
- [x] migration upgrade succeeds
- [x] migration downgrade succeeds
- [x] stable semantic question keys are used (e.g. `personal.first_name`)
- [x] displayed text is not used as question identity
- [x] approved database question is checked before AI
- [x] approved user-language translation is preferred
- [x] static form translation is used before AI
- [x] AI translation runs only when needed (stores as pending review)
- [x] AI generation runs only as a final language-aware fallback (stores as pending review)
- [x] deterministic fallback works without AI
- [x] AI content defaults to pending review
- [x] approved manual content is never overwritten automatically
- [x] pending content is not globally reused by default
- [x] repeated approved questions cause zero AI calls
- [x] question resolution does not alter workflow state or progress
- [x] session ownership remains enforced
- [x] at least 11 common semantic questions are seeded
- [x] approved `en`, `de`, `fr`, and `ar` translations exist for seeded questions
- [x] automated tests make no real AI calls
- [x] backend tests pass
- [x] frontend tests pass
- [x] Ruff linting passes
- [x] Ruff formatting passes
- [x] mypy passes
- [x] ESLint passes
- [x] TypeScript checking passes
- [x] documentation is updated (including ADR 0005)
- [x] no vector search, embeddings, OCR, upload, PDF, auth, payment, Redis, Celery, or object storage was implemented
- [x] `TODO.md` contains final verification results


## Planned Steps

- [x] Create Git branch `feature/reusable-question-catalog`
- [x] Archive Phase 5 TODO in `docs/progress/phase-5-local-ollama-provider.md`
- [x] Define SQLAlchemy database models: `QuestionDefinition`, `QuestionTranslation`, and `QuestionResolutionLog` (or audit logs)
- [x] Create Alembic migration upgrade/downgrade scripts for the new tables and run the upgrade
- [x] Implement the repository layer (`QuestionDefinitionRepository`, `QuestionTranslationRepository`, `QuestionResolutionLogRepository`)
- [x] Seed at least 11 common semantic questions with approved translations for `en`, `de`, `fr`, and `ar`
- [x] Implement prompt templates for question translation and generation: `translate_question_v1.txt` and `generate_question_v1.txt`
- [x] Implement `QuestionCatalogService` to manage/access definitions and manual translations
- [x] Implement `QuestionReviewService` for manual review transitions (approve/reject pending translations)
- [x] Implement `QuestionResolver` with hybrid lookup flow (database first, static fallback, AI translation, AI generation, deterministic fallback)
- [x] Expose administrative/development endpoints for listing catalog, creating translations, and reviewing translations
- [x] Integrate resolved questions into the `GET /api/form-sessions/{session_id}/current-question` endpoint (and extend current-field response)
- [x] Write unit tests for repositories, catalog, resolver logic, AI calls deduplication, and endpoint security/access
- [x] Run full verification checks (Ruff check, formatting, mypy types check, pytest backend/frontend tests)
- [x] Update project documentation: architecture, question-catalog, ADR 0005, README.md, config settings

## Files Expected to Change

- `TODO.md`
- `.env.example`
- `backend/app/core/config.py`
- `backend/app/models/` (or new models file/directory)
- `backend/app/database/` (for migration)
- `backend/app/questions/` (new module: schemas, repositories, services, api)
- `backend/app/ai/prompts/translate_question_v1.txt` (new)
- `backend/app/ai/prompts/generate_question_v1.txt` (new)
- `backend/app/sessions/api/routes.py`
- `backend/app/main.py`
- `backend/tests/questions/` (new tests)
- `docs/question-catalog.md` (new)
- `docs/decisions/0005-hybrid-question-resolution.md` (new)
- `docs/architecture.md`
- `docs/form-model.md`
- `docs/workflow.md`
- `docs/ai-provider.md`
- `docs/testing.md`
- `docs/privacy.md`
- `docs/security.md`
- `README.md`

## Decisions and Assumptions

- We will implement three tables: `question_definitions`, `question_translations`, and `question_resolution_logs`.
- Semantic keys (e.g. `personal.first_name`) will be used as unique lookup identifiers.
- Production behavior will default to approved-only database translation lookup or deterministic fallback unless pending reuse configuration is explicitly turned on.
- No semantic vector databases or similarity search will be added; matching is exact/by key.
- Administration endpoints are development/mock only, protected behind a developer guard configuration.

## Blockers

- None

## Verification

- [x] Backend tests pass
- [x] Frontend tests pass
- [x] Linting passes
- [x] Formatting passes
- [x] Type checking passes
- [x] Acceptance criteria were manually verified

## Completed

- Created Git branch `feature/reusable-question-catalog`
- Archived Phase 5 TODOs in `docs/progress/phase-5-local-ollama-provider.md`
- Reset root `TODO.md` for Phase 6
- Implemented models, repositories, and resolver for reusable question catalog
- Created Alembic database migration
- Seeded catalog with 11 core question keys and approved `en`, `de`, `fr`, and `ar` translations
- Developed prompt templates and extended mock/Ollama provider signatures
- Added catalog list/review administration routes and integrated resolver inside workflow sessions
- Wrote and verified 100% test coverage for Resolver, Review Service, and Session API Integration
- Verified formatting, linting (Ruff), types (mypy), and all tests pass on frontend and backend
