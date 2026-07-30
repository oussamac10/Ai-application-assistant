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

**Status: not started.** This is a clean cut only — branch created, roadmap and phase docs updated,
`TODO.md` reset. No Phase 15 code has been written.

## Goal

Extract the `TranslationProvider` abstraction named in `docs/claude/domain-rules.md`, and implement
Azure Translator behind it as the provider for translating question labels, choice options and
other display text — replacing the local model for that specific job.

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

## Open questions to settle before implementing

1. **Which Azure Translator resource/region**, and is the key already provisioned? (Phase 14's
   `.env` pattern: real values in the git-ignored root `.env`, empty placeholders in
   `.env.example`.)
2. **Does Ollama remain a selectable translation provider**, or does Azure become the only one once
   configured? Keeping Ollama is the safer default and costs little.
3. **Source-language handling.** Detected text is currently *assumed* to be the default source
   language, so the German contract's labels take an `en -> de` round trip that mostly returns them
   unchanged. Azure Translator can auto-detect the source language per request, which would fix
   most of the waste — but it changes behaviour beyond a provider swap. In or out of this phase?

## Carried Deferred Items

- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10).
- Pre-existing Ruff formatting exceptions under `app/documents/*` and `tests/documents/`.
- Preparation is still synchronous; background jobs with progress polling remain Phase 20.
- The translation cache is process-local and dropped on restart.
