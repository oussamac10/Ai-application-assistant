# AI Provider

This document describes the AI provider system for the form-filling assistant.

---

## Overview

The backend uses a **provider abstraction layer** to decouple business logic
from any specific AI implementation.  All business services import the
`AIProvider` Protocol; they never import a concrete class directly.

```
Business service
     │
     ▼
AIProvider (Protocol)
     │
     ├── MockAIProvider      (deterministic, no network, default in tests/dev)
     └── OllamaAIProvider    (local Ollama instance, Phase 5+)
```

---

## AIProvider Protocol

Defined in `backend/app/ai/mock_provider.py`:

```python
class AIProvider(Protocol):
    async def extract_value(self, request: ExtractionRequest) -> ExtractionResult: ...
    async def explain_field(self, request: ExplanationRequest) -> ExplanationResult: ...
    async def clarify_answer(self, request: ClarificationRequest) -> ClarificationResult: ...
    async def translate_output(self, request: TranslationRequest) -> TranslationResult: ...
    async def health_check(self) -> bool: ...
```

---

## Schemas

All request and result types are in `backend/app/ai/schemas.py`.

| Schema               | Description                                  |
|----------------------|----------------------------------------------|
| `ExtractionRequest`  | Field type, answer, language codes           |
| `ExtractionResult`   | Normalized value, output value, clarification|
| `ExplanationRequest` | Field label/type in source language          |
| `ExplanationResult`  | Explanation text in user language            |
| `ClarificationRequest` | Partial value, uncertainties             |
| `ClarificationResult`  | Missing fields, follow-up question       |
| `TranslationRequest` | Text, source and target language codes       |
| `TranslationResult`  | Translated text                              |

All schemas use `ConfigDict(populate_by_name=True)` so both snake_case and
camelCase field names work.

---

## Provider Selection

The provider is selected at startup via the `AI_PROVIDER` environment variable.

```env
AI_PROVIDER=mock    # default for local development and all tests
AI_PROVIDER=ollama  # use a local Ollama instance
```

The factory is in `backend/app/ai/factory.py`.  Unsupported provider names
fail fast at startup with `AIProviderConfigurationError`.

A process-level singleton is maintained so the provider is constructed once.
FastAPI routes receive the provider via `Depends(get_ai_provider)`.

---

## MockAIProvider

`backend/app/ai/mock_provider.py`

Fully deterministic.  Identical inputs always produce identical outputs.
No external calls.  Handles all 14 field types defined in the form model.

**Use for**: all automated tests, local development without Ollama.

---

## OllamaAIProvider

`backend/app/ai/ollama_provider.py`

| Setting                          | Default                           | Description                         |
|----------------------------------|-----------------------------------|-------------------------------------|
| `OLLAMA_BASE_URL`                | `http://host.docker.internal:11434` | Ollama HTTP base URL              |
| `OLLAMA_MODEL`                   | `qwen3:4b`                        | Model name                          |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | `60`                              | Per-request timeout                 |
| `OLLAMA_MAX_RETRIES`             | `1`                               | Retries after timeout               |
| `OLLAMA_CACHE_ENABLED`           | `false`                           | Enable in-memory response cache     |

### How it works

1. A versioned prompt template is loaded from `backend/app/ai/prompts/`.
2. The template is filled with field metadata, language codes, and the
   user's answer.
3. The filled prompt is posted to `POST /api/generate` with
   `stream: false` and `format: "json"`.
4. The `response` field of the Ollama response is parsed as JSON.
5. Pydantic validates the parsed JSON against the expected schema.
6. The validated result is returned to the service layer.

### Error hierarchy

```
AIProviderError
├── AIProviderUnavailableError    → HTTP 503
├── AIProviderTimeoutError        → HTTP 504
├── AIProviderMalformedResponseError → HTTP 502
├── AIProviderValidationError     → HTTP 502
└── AIProviderConfigurationError  → HTTP 500
```

All errors are mapped to safe HTTP responses in `app/main.py`.
No error messages expose raw prompts, model responses, or internal details.

---

## Prompt Files

Stored in `backend/app/ai/prompts/`.  File names include a version suffix
so new prompts can be deployed without breaking existing sessions.

| File                     | Purpose                                 |
|--------------------------|-----------------------------------------|
| `extract_value_v1.txt`   | Extract canonical value from free text  |
| `explain_field_v1.txt`   | Explain a form field to the user        |
| `clarify_answer_v1.txt`  | Ask for missing information             |
| `translate_output_v1.txt`| Translate dynamic text                  |

All prompt templates contain an instruction to treat user-supplied text as
**data only**, never as system instructions.

---

## In-Memory Cache

`backend/app/ai/cache.py`

Disabled by default (`OLLAMA_CACHE_ENABLED=false`).  When enabled, it caches
`ExtractionResult` objects keyed by SHA-256 of the serialised request.  The
cache lives for the lifetime of the process and is not persisted to disk.

**Privacy note**: cached values contain normalised form-field content.
Enable caching only when the privacy implications are understood and accepted.

---

## Health Endpoint

```
GET /api/health/ai
```

Returns `200 {"status": "ok", "provider": "..."}` when the provider is
healthy, `503` when unavailable.  No configuration details are exposed.

---

## Evaluation CLI

```bash
cd backend
python -m app.commands.evaluate_ai_provider --verbose
```

Options:

| Flag             | Default                           | Description                  |
|------------------|-----------------------------------|------------------------------|
| `--fixtures-dir` | `fixtures/ai/evaluation/`         | Directory of JSON fixtures   |
| `--verbose`      | off                               | Print all results            |

Fixtures in `fixtures/ai/evaluation/` use fictional data only.
No real applicant information is committed.
No paid AI service is called.

The command exits with code 1 if any fixture fails or no fixtures are found.

---

## Automated Tests

| Test file                              | What it tests                                   |
|----------------------------------------|-------------------------------------------------|
| `tests/ai/test_factory.py`             | Factory selection, protocol satisfaction        |
| `tests/ai/test_ollama_provider.py`     | HTTP mocking, timeout, connect error, health    |
| `tests/ai/test_cache.py`              | Cache enable/disable, key stability, clear      |
| `tests/ai/test_health.py`             | `/api/health/ai` endpoint for ok and 503 cases  |
| `tests/ai/test_eval_command.py`       | Fixture count, MockAIProvider pass rate         |

All tests use `MockAIProvider` or mocked HTTP — no real Ollama calls.

---

## Local Development with Ollama

1. Install Ollama: <https://ollama.com>
2. Pull the model: `ollama pull qwen3:4b`
3. Confirm it is running: `ollama list`
4. Set environment variable: `AI_PROVIDER=ollama`
5. Start the backend: `uvicorn app.main:app --reload`
6. Check health: `curl http://localhost:8000/api/health/ai`

When running the backend in Docker:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

> **Linux note**: `host.docker.internal` may not resolve automatically on
> Linux.  Add `--add-host=host.docker.internal:host-gateway` to the Docker
> run command, or use the host machine IP address.

---

## Future Providers

To add a new provider:

1. Create `backend/app/ai/<name>_provider.py` implementing the `AIProvider` Protocol.
2. Add the provider name to `_SUPPORTED_PROVIDERS` in `app/core/config.py`.
3. Add a case to `build_provider()` in `app/ai/factory.py`.
4. Add any required settings to `app/core/config.py` and `.env.example`.
5. Write tests with mocked HTTP; no real calls in automated tests.
6. Create an ADR documenting the decision.
