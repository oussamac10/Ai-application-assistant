# Project TODO

## Current Task

Integrating local Ollama AI provider into the existing deterministic answer workflow (MVP Phase 5).

## Goal

Add `OllamaAIProvider`, provider factory, structured response validation, versioned prompts, retry/timeout handling, optional in-memory cache, AI health endpoint, evaluation fixtures, and evaluation CLI command — while keeping `MockAIProvider` working and all existing tests passing.

## Acceptance Criteria

- [x] Phase 4 TODO details are archived in `docs/progress/phase-4-mock-answer-workflow.md`
- [x] root `TODO.md` reset for Phase 5
- [x] branch is `feature/ollama-ai-provider`
- [x] `OllamaAIProvider` exists
- [x] provider factory supports `mock` and `ollama`
- [x] unsupported providers fail fast at startup
- [x] automated tests make no real Ollama calls
- [x] no cloud AI provider exists
- [x] structured model responses are validated with Pydantic
- [x] malformed responses are rejected safely
- [x] timeout handling works
- [x] retries are bounded
- [x] deterministic validation always runs after AI extraction
- [x] original answers remain preserved
- [x] provider failures do not corrupt workflow state
- [x] prompt files are versioned
- [x] prompts contain minimal context
- [x] AI requests exclude tokens and secrets
- [x] provider health endpoint works (`GET /api/health/ai`)
- [x] at least 30 fictional evaluation fixtures exist
- [x] evaluation CLI command works
- [x] backend container connectivity is documented
- [x] caching disabled by default
- [x] backend tests pass
- [x] frontend tests pass
- [x] Ruff linting passes
- [x] Ruff formatting passes
- [x] mypy passes
- [x] ESLint passes
- [x] TypeScript checking passes
- [x] documentation is updated
- [x] ADR 0004 is created
- [x] no OCR, upload, PDF, auth, payment, Redis, Celery, or object-storage was implemented
- [x] `TODO.md` contains final verification results

## Planned Steps

- [x] Create Git branch `feature/ollama-ai-provider`
- [x] Archive Phase 4 TODO in `docs/progress/phase-4-mock-answer-workflow.md`
- [x] Expand AI schemas: add `ExplanationRequest/Result`, `ClarificationRequest/Result`, `TranslationRequest/Result`; add structured Ollama response models
- [x] Expand `AIProvider` Protocol and update `MockAIProvider` with all new methods
- [x] Add AI config to `Settings` (`AI_PROVIDER`, `OLLAMA_*`, `AI_ALLOW_MOCK_FALLBACK`)
- [x] Implement `AIProviderFactory` selecting `MockAIProvider` or `OllamaAIProvider`
- [x] Create versioned prompt text files in `backend/app/ai/prompts/`
- [x] Implement `OllamaAIProvider` with httpx, timeouts, retries, structured JSON, Pydantic validation
- [x] Implement `AIResponseCache` (in-memory, disabled by default)
- [x] Implement provider error classes (`AIProviderUnavailableError`, etc.)
- [x] Update `AnswerService` to accept an injected provider (not hard-coded `MockAIProvider`)
- [x] Update routes to get provider from factory / dependency injection
- [x] Add `GET /api/health/ai` endpoint
- [x] Register new error handlers in `main.py`
- [x] Create 30+ fictional evaluation fixtures in `fixtures/ai/evaluation/`
- [x] Implement `python -m app.commands.evaluate_ai_provider` CLI
- [x] Write tests: factory, Ollama HTTP (mocked), validation, retry, cache, health, eval command
- [x] Run full quality checks (Ruff, Mypy, ESLint, tsc, pytest)
- [x] Update `.env.example`; create ADR 0004; update all docs

## Files Expected to Change

- `TODO.md`
- `.env.example`
- `backend/app/ai/schemas.py`
- `backend/app/ai/mock_provider.py`
- `backend/app/ai/ollama_provider.py` (new)
- `backend/app/ai/factory.py` (new)
- `backend/app/ai/cache.py` (new)
- `backend/app/ai/errors.py` (new)
- `backend/app/ai/prompts/extract_value_v1.txt` (new)
- `backend/app/ai/prompts/explain_field_v1.txt` (new)
- `backend/app/ai/prompts/clarify_answer_v1.txt` (new)
- `backend/app/ai/prompts/translate_output_v1.txt` (new)
- `backend/app/core/config.py`
- `backend/app/api/health.py`
- `backend/app/answers/services.py`
- `backend/app/answers/api/routes.py`
- `backend/app/main.py`
- `backend/app/commands/evaluate_ai_provider.py` (new)
- `backend/tests/ai/test_factory.py` (new)
- `backend/tests/ai/test_ollama_provider.py` (new)
- `backend/tests/ai/test_cache.py` (new)
- `backend/tests/ai/test_health.py` (new)
- `backend/tests/ai/test_eval_command.py` (new)
- `fixtures/ai/evaluation/*.json` (30+ files)
- `docs/ai-provider.md`
- `docs/architecture.md`
- `docs/workflow.md`
- `docs/testing.md`
- `docs/privacy.md`
- `docs/security.md`
- `docs/decisions/0004-local-ollama-provider.md`
- `README.md`

## Decisions and Assumptions

- `httpx` (already installed) is used as the async HTTP client for Ollama API calls.
- Ollama is called with `stream: false` and `format: "json"` for structured output.
- `MockAIProvider` implements all Protocol methods; it returns sensible deterministic results.
- Provider is injected into `AnswerService` via a parameter; routes get the provider from a FastAPI dependency that calls the factory.
- In-memory cache uses a plain dict keyed by a hash of the request parameters; TTL is not implemented in Phase 5 (cache lives for the process lifetime or until restarted).
- Tests use `pytest-mock` / `unittest.mock` to patch `httpx.AsyncClient` — no real HTTP calls.
- Evaluation fixtures use fictional names, dates, and amounts only.

## Blockers

- None

## Verification

- [x] Backend tests pass — 54/54 (Ruff, mypy, pytest all clean)
- [x] Linting passes — Ruff: All checks passed
- [x] Formatting passes — Ruff format: 0 changes
- [x] Type checking passes — mypy: no issues in 47 files
- [x] Evaluation CLI runs: 22/32 MockAIProvider passes (expected for semantic fixtures)
- [x] Branch committed: `feature/ollama-ai-provider` (3607fde), not merged

## Completed

- Created Git branch `feature/ollama-ai-provider`
- Archived Phase 4 TODOs in `docs/progress/phase-4-mock-answer-workflow.md`
- Reset root `TODO.md` for Phase 5
