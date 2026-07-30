# TODO

## Completed Phases

Archived under `docs/progress/`:

1. Project Foundation
2. Form Definitions and Versioning
3. Temporary Anonymous Sessions
4. Mock Question and Answer Workflow
5. Local AI Integration with Ollama
6. Reusable Question Catalog and Hybrid Resolution
7. Frontend Guided Form Experience
8. PDF Template Mapping and Export
9. Form Upload and Document Analysis
10. OCR Integration
11. Dynamic Form Field Detection
12. User Accounts and Saved Applications
13. Automatic Upload-to-Questions User Flow
14. Azure Document Intelligence Provider

## Current Task

Phase 15 — Azure Translator Integration. Branch `feature/azure-translator`, based on
`feature/azure-document-intelligence`.

**Status: in progress.** Phase 15 has started. Implement the provider abstraction, Azure adapter,
configuration, safe fallbacks, tests, documentation, and before/after benchmark.

## Goal

Extract the `TranslationProvider` abstraction named in `docs/claude/domain-rules.md`, and implement
Azure Translator behind it as the provider for translating question labels, choice options and
other display text — replacing the local model for that specific job.

## Confirmed implementation decisions

1. Azure Translator is the primary translation provider when configured.
2. Ollama remains available as a selectable fallback provider.
3. Azure automatic source-language detection is included in Phase 15 to avoid incorrect and wasteful
   forced `en -> target` translation paths for non-English source documents.
4. Approved catalog translations, persisted translations, and cache hits must still win before any
   provider call.
5. Only the current user-interface language is translated eagerly during question preparation.
6. Output-language translation remains deferred until it is actually needed by review or export.
7. Real Azure credentials stay in the git-ignored root `.env`; `.env.example` contains empty
   placeholders only.
8. Automated tests must mock Azure and must never call the live service.

## Why this phase, in one paragraph

Translation currently rides on `AIProvider`, which conflates language understanding (extraction,
clarification, question generation) with plain text translation. Phase 14's measurements make the
cost of that conflation concrete: on the reference German rental contract, `prepare-questions`
takes **43.8 s**, of which **34.3 s** is local-model translation — and that is *after* batching cut
the call count from 28 to 4. The remaining time is the model generating text, which a dedicated
translation service does in a single array request.

## Starting point (measured, Phase 14)

| | value |
|---|---|
| `total_duration` | 43.80 s |
| `translation_duration` | 34.27 s (78% of the request) |
| `ollama_call_count` | 4 (3 batched chunks + 1 per-item fallback) |
| `unique_texts` | 28 |
| generated questions | 24 |
| repeat request | 0.09 s, 0 AI calls, session reused |

These are the numbers Phase 15 has to improve on, and the same measurement should be repeated at
the end for a like-for-like before/after.

## Implementation checklist

- [ ] Add a `TranslationProvider` protocol and provider factory.
- [ ] Keep deterministic mock and Ollama translation implementations.
- [ ] Add `AzureTranslatorProvider` using one array request per target language when possible.
- [ ] Add backend-only `AZURE_TRANSLATOR_*` configuration and Docker passthrough.
- [ ] Validate Azure configuration only when Azure is selected.
- [ ] Add bounded timeout, one bounded retry, safe error mapping, and request-ID capture.
- [ ] Map positional Azure results back to stable caller IDs explicitly.
- [ ] Validate partial, missing, duplicate, and malformed results per item.
- [ ] Preserve approved-catalog, persisted-translation, cache, and deterministic fallback order.
- [ ] Add source-language auto-detection while preserving the detected source metadata.
- [ ] Translate only the current user language eagerly.
- [ ] Keep output-language translation deferred.
- [ ] Record request count, translated character count, cache hits, provider latency, and fallbacks.
- [ ] Ensure API keys and raw provider responses never appear in logs or frontend responses.
- [ ] Add unit, integration, regression, ownership, RTL, and idempotency tests.
- [ ] Update ADR, phase docs, architecture, security, privacy, README, and `.env.example`.
- [ ] Benchmark the German rental contract before and after.
- [ ] Test the Arabic digital form and verify Arabic/RTL behavior.
- [ ] Run backend and frontend quality gates.
- [ ] Commit and push the completed phase.

## Performance targets

- Uncached translation duration: preferably under 3 seconds for the 24-question reference form.
- Total preparation duration: preferably under 15 seconds on the same environment.
- Repeat preparation: zero provider calls and approximately the existing 0.09-second path.

## Carried Deferred Items

- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10).
- Pre-existing Ruff formatting exceptions under `app/documents/*` and `tests/documents/`.
- Preparation is still synchronous; background jobs with progress polling remain Phase 20.
- The translation cache is process-local and dropped on restart.
