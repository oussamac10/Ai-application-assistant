# Project TODO

## Current Task

Integrating local Ollama AI provider into the existing deterministic answer workflow (MVP Phase 5).

## Goal

Add `OllamaAIProvider`, provider factory, structured response validation, versioned prompts, retry/timeout handling, optional in-memory cache, AI health endpoint, evaluation fixtures, and evaluation CLI command — while keeping `MockAIProvider` working and all existing tests passing.

## Acceptance Criteria

- [x] Phase 4 TODO details are archived in `docs/progress/phase-4-mock-answer-workflow.md`
- [ ] root `TODO.md` reset for Phase 5
- [ ] branch is `feature/ollama-ai-provider`
- [ ] `OllamaAIProvider` exists
- [ ] provider factory supports `mock` and `ollama`
- [ ] unsupported providers fail fast at startup
- [ ] automated tests make no real Ollama calls
- [ ] no cloud AI provider exists
- [ ] structured model responses are validated with Pydantic
- [ ] malformed responses are rejected safely
- [ ] timeout handling works
- [ ] retries are bounded
- [ ] deterministic validation always runs after AI extraction
- [ ] original answers remain preserved
- [ ] provider failures do not corrupt workflow state
- [ ] prompt files are versioned
- [ ] prompts contain minimal context
- [ ] AI requests exclude tokens and secrets
- [ ] provider health endpoint works (`GET /api/health/ai`)
- [ ] at least 30 fictional evaluation fixtures exist
- [ ] evaluation CLI command works
- [ ] backend container connectivity is documented
- [ ] caching disabled by default
- [ ] backend tests pass
- [ ] frontend tests pass
- [ ] Ruff linting passes
- [ ] Ruff formatting passes
- [ ] mypy passes
- [ ] ESLint passes
- [ ] TypeScript checking passes
- [ ] documentation is updated
- [ ] ADR 0004 is created
- [ ] no OCR, upload, PDF, auth, payment, Redis, Celery, or object-storage was implemented
- [ ] `TODO.md` contains final verification results

## Planned Steps

- [x] Create Git branch `feature/ollama-ai-provider`
- [x] Archive Phase 4 TODO in `docs/progress/phase-4-mock-answer-workflow.md`
- [ ] Expand AI schemas: add `ExplanationRequest/Result`, `ClarificationRequest/Result`, `TranslationRequest/Result`; add structured Ollama response models
- [ ] Expand `AIProvider` Protocol and update `MockAIProvider` with all new methods
- [ ] Add AI config to `Settings` (`AI_PROVIDER`, `OLLAMA_*`, `AI_ALLOW_MOCK_FALLBACK`)
- [ ] Implement `AIProviderFactory` selecting `MockAIProvider` or `OllamaAIProvider`
- [ ] Create versioned prompt text files in `backend/app/ai/prompts/`
- [ ] Implement `OllamaAIProvider` with httpx, timeouts, retries, structured JSON, Pydantic validation
- [ ] Implement `AIResponseCache` (in-memory, disabled by default)
- [ ] Implement provider error classes (`AIProviderUnavailableError`, etc.)
- [ ] Update `AnswerService` to accept an injected provider (not hard-coded `MockAIProvider`)
- [ ] Update routes to get provider from factory / dependency injection
- [ ] Add `GET /api/health/ai` endpoint
- [ ] Register new error handlers in `main.py`
- [ ] Create 30+ fictional evaluation fixtures in `fixtures/ai/evaluation/`
- [ ] Implement `python -m app.commands.evaluate_ai_provider` CLI
- [ ] Write tests: factory, Ollama HTTP (mocked), validation, retry, cache, health, eval command
- [ ] Run full quality checks (Ruff, Mypy, ESLint, tsc, pytest)
- [ ] Update `.env.example`; create ADR 0004; update all docs

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

- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Linting passes
- [ ] Formatting passes
- [ ] Type checking passes
- [ ] Acceptance criteria were manually verified

## Completed

- Created Git branch `feature/ollama-ai-provider`
- Archived Phase 4 TODOs in `docs/progress/phase-4-mock-answer-workflow.md`
- Reset root `TODO.md` for Phase 5
