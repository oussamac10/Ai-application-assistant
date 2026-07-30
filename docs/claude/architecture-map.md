# Architecture Map

## Backend

- `backend/app/main.py`: FastAPI setup and routes
- `backend/app/core/config.py`: configuration
- `backend/app/database/`: database infrastructure
- `backend/app/forms/`: form definitions and versions
- `backend/app/sessions/`: anonymous sessions and ownership
- `backend/app/questions/`: catalog and answer resolution
- `backend/app/ai/`: Ollama/provider abstractions and single-text translation
  (`text_translation.py`); batched translation moved to `app/translation/` in Phase 15
- `backend/app/pdf/`: PDF mappings and export
- `backend/app/documents/`: upload, storage, validation, analysis
- `backend/app/ocr/`: local OCR provider abstraction, page rendering, OCR API
- `backend/app/field_detection/`: dynamic field-detection provider abstraction, extraction, review API, question-generation bridge, Phase 13 confidence routing (`confidence.py`) and orchestration (`orchestration.py`)
- `backend/app/language/`: Phase 15 document-language detection
  (`detector.py`), filtered sampling (`sampling.py`), persistence/reuse and
  precedence (`service.py`)
- `backend/app/translation/`: Phase 15 `TranslationProvider` abstraction (mock/Ollama/Azure
  Translator), provider factory, translation pipeline (`service.py`), deterministic
  identifier protection (`protected.py`), deferred-language backfill (`backfill.py`)
- `backend/app/auth/`: user accounts, Argon2id password hashing, HMAC auth-session tokens, cookie/CSRF dependencies
- `backend/app/applications/`: persistent application history (list/detail/rename/delete) and anonymous-to-account claim flow, built on `FormSession`
- `backend/app/commands/`: cleanup and fixture-seeding commands
- `backend/migrations/`: Alembic migrations
- `backend/tests/`: backend tests

## Frontend

- `frontend/src/app/application/`: application flow
- `frontend/src/features/form-session/`: guided session
- `frontend/src/features/document-upload/`: Phase 9 upload UI; drives the Phase 13 automatic upload-to-questions flow after upload
- `frontend/src/features/document-ocr/`: Phase 10 OCR status/result UI (admin/debug only as of Phase 13)
- `frontend/src/features/field-detection/`: Phase 11 field-detection review UI (admin/debug only as of Phase 13, gated by `debugMode.ts`); Phase 13's `prepareQuestions` API client
- `frontend/src/features/auth/`: Phase 12 login/register/account menu, auth context and API client
- `frontend/src/features/applications/`: Phase 12 My Applications (resume/rename/delete), claim-into-account prompt
- `frontend/messages/`: en, de, fr, ar
- Check the repository before choosing the Playwright test directory.

## Project

- `fixtures/pdf/`: controlled PDF fixtures
- `docs/decisions/`: ADRs
- `docs/progress/`: archived phase TODOs
- `TODO.md`: current phase only
