# ADR 0004: Local AI Integration with Ollama

**Date**: 2026-07-24
**Status**: Accepted
**Branch**: feature/ollama-ai-provider

---

## Context

Phase 4 used `MockAIProvider` for deterministic answer extraction.
Phase 5 introduces support for a real local language model via Ollama running
on the developer machine.

The backend runs in Docker and must reach Ollama using
`http://host.docker.internal:11434`.

The model available on the developer machine is `qwen3:4b`.

---

## Decision

### Provider abstraction (unchanged from Phase 4)

The existing `AIProvider` Protocol is expanded with four methods:

| Method            | Purpose                                    |
|-------------------|--------------------------------------------|
| `extract_value`   | Extract a canonical value from free text   |
| `explain_field`   | Explain a form field in the user language  |
| `clarify_answer`  | Ask a follow-up for incomplete answers     |
| `translate_output`| Translate dynamic user-supplied text       |
| `health_check`    | Return `True` when the provider is online  |

Business services import only the Protocol; never a concrete implementation.

### Provider factory

`app.ai.factory.build_provider()` reads `settings.AI_PROVIDER` and
instantiates the correct concrete class:

| `AI_PROVIDER` | Class              |
|---------------|--------------------|
| `mock`        | `MockAIProvider`   |
| `ollama`      | `OllamaAIProvider` |

Unsupported values raise `AIProviderConfigurationError` at startup.

A process-level singleton (`_provider`) is maintained so the provider is
constructed once, not once per request.

### OllamaAIProvider design

- Uses `httpx.AsyncClient` for async HTTP calls.
- Calls `/api/generate` with `stream=false` and `format="json"`.
- Timeout: configurable via `OLLAMA_REQUEST_TIMEOUT_SECONDS` (default 60 s).
- Retries: configurable via `OLLAMA_MAX_RETRIES` (default 1).
- Pydantic validates structured responses before any value is used.
- Malformed JSON → `AIProviderMalformedResponseError`.
- Validation failure → `AIProviderValidationError`.
- Timeout → `AIProviderTimeoutError`.
- Connection refused → `AIProviderUnavailableError`.

### Prompt files

Versioned prompt templates are stored in `backend/app/ai/prompts/`.
Each template uses `{{variable}}` placeholders.
User-supplied text is always labelled as **untrusted data** in the prompt.

| File                     | Purpose                       |
|--------------------------|-------------------------------|
| `extract_value_v1.txt`   | Main field extraction prompt  |
| `explain_field_v1.txt`   | Field explanation prompt      |
| `clarify_answer_v1.txt`  | Follow-up clarification prompt|
| `translate_output_v1.txt`| Dynamic translation prompt    |

### Caching

An in-memory `AIResponseCache` is available but **disabled by default**.
When enabled (`OLLAMA_CACHE_ENABLED=true`), it caches responses for the
lifetime of the process using SHA-256 keyed lookup.

### Health endpoint

`GET /api/health/ai` returns 200 when the provider is healthy, 503 when not.
No sensitive configuration values are exposed in the response.

### Evaluation CLI

`python -m app.commands.evaluate_ai_provider` runs the configured provider
against 32+ fictional fixtures in `fixtures/ai/evaluation/`.
Paid AI services are never called in automated tests.

---

## Consequences

### Positive

- Real language model can be used locally without cloud costs.
- `MockAIProvider` remains the default; no existing tests are affected.
- Deterministic validation still runs after every extraction.
- Provider can be swapped by changing one environment variable.

### Negative / Trade-offs

- Ollama must be running on the host machine when `AI_PROVIDER=ollama`.
- The `host.docker.internal` address does not work on Linux without extra Docker config.
- Model quality depends on the chosen Ollama model; results may vary.

### Not implemented in Phase 5

- Persistent response cache (TTL, eviction).
- Cloud AI provider.
- Automatic mock fallback when Ollama is unavailable.
- Celery, Redis, object storage, OCR, file uploads.
