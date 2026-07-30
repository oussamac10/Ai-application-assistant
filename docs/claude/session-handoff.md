# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Phase 14 (Azure Document Intelligence) detection was already correct — 24 usable fields, 24
generated questions — but users still saw a processing error. This session found and fixed why,
in two parts.

**1. Nobody owned the request-duration budget.** Reproduced through the Next proxy exactly as the
browser calls it: `POST /prepare-questions` returned **HTTP 500 at 30.08 s** with the plain-text
body `Internal Server Error` (not the API's `{code, message, stage}` JSON), and the frontend
container logged `Failed to proxy … socket hang up`. That is Next.js's rewrite proxy abandoning
the upstream request after its default 30 s. The backend was unaffected and finished successfully
*after* the proxy had already answered the browser — so a document that worked was reported as
failed, and the session it created was never reached.

**2. Question generation cost one AI call per text.** `question_bridge` translated each field
label and each choice option in its own sequential call: **28 Ollama calls, 41.4 s** with
detection cached. A negative margin against a 30 s ceiling, so the failure was deterministic.

Fixes:

1. `app/ai/batch_translation.py` (new) — batched, deduplicated, cached translation resolved
   cheapest-first: dedup, process-local LRU, approved catalog translations
   (`QuestionRepository.get_approved_translation`, per `domain-rules.md`), then the provider in
   bounded chunks. `AIProvider` gained `translate_output_batch` (Ollama + mock).
2. Results map back **by request id, never by response position**, so a reordered/partial/repeated
   provider response can never move one field's translation onto another field.
3. Batch entries are validated **individually**. Whole-response validation was tried first and was
   wrong: a real local-model reply contained `"id": ": 1"` among three valid entries and all four
   were discarded. Now only the malformed entry is dropped and falls back on its own.
4. `TextTranslation.succeeded` — failure can no longer be inferred by comparing input to output. A
   legitimate translation is often identical to its source (German label into German, `IBAN`), and
   that was being counted and logged as a failure (`untranslated=4`).
5. Bounded concurrency across chunks (`AI_TRANSLATION_CONCURRENCY`, default 3). Batching alone cut
   calls 28 -> 4 but barely moved wall time, since three sequential ~15 s generations dominate.
6. `next.config.js`: `experimental.proxyTimeout = 180_000`.
7. Frontend: `prepareQuestions` shares one in-flight promise per document+languages; each
   processing run carries a generation id and may only write state while current, so a superseded
   attempt cannot overwrite a newer success; a success always clears a stale error; a *bare*
   gateway failure (transport, 502/504, or 500 with no error code) is retried up to twice instead
   of showing an error, which is safe because the endpoint is idempotent.
8. Structured timing logs at every stage (`azure_duration`, `normalization_duration`,
   `detection_duration`, `translation_duration`, `question_resolution_duration`,
   `ollama_call_count`, `total_duration`) — counts and durations only, never document text.

## Repository state

- Branch: `feature/azure-document-intelligence`
- Docker Compose `backend` and `frontend` rebuilt this session; `proxyTimeout = 180000` and
  `AI_TRANSLATION_BATCH_SIZE=12` / `AI_TRANSLATION_CONCURRENCY=3` verified live inside the
  containers.
- The dev database's `basic-registration` fixture was re-seeded after the pytest `TRUNCATE`
  cleanup, as in every prior phase verification.

## Measured result (reference PDF, fresh upload, through the proxy)

| | before | after |
|---|---|---|
| HTTP status | 500 | 200 |
| total duration | 30.08 s (abandoned) | 43.84 s (completed) |
| Ollama calls | 28 | 4 |
| generated questions | 24 (never delivered) | 24 |
| frontend result | processing error | first question `vermieter_name` |
| repeat request | — | 0.09 s, 0 AI calls, `reusedExistingSession: true` |

Stage split of the "after" run: `azure_duration=8.77s`, `normalization_duration=0.01s`,
`detection_duration=8.90s`, `translation_duration=34.27s`,
`question_resolution_duration=34.88s`, `total_duration=43.80s`.

## Verification results

Backend **474 passed**, ruff clean, `ruff format --check` clean on changed files, mypy clean
(136 files). Frontend **129 passed**, ESLint and `tsc --noEmit` clean. See `TODO.md` for the exact
per-suite breakdown and the Playwright result.

## Known limitation carried forward

- **Most of the remaining 34 s of translation is avoidable.** The contract is German, but detected
  text is *assumed* to be the default source language (`en`) because field detection performs no
  document-language detection, so German labels take an `en -> de` round trip that mostly returns
  them unchanged. Fixing it changes detection behaviour, so it was left out of scope here.
- Preparation is still synchronous (43.8 s). Background jobs + progress polling is Phase 17.
- The translation cache is process-local and dropped on restart.
- `experimental.proxyTimeout` is an experimental Next 14 option.
- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9).

## Next action

Phase 14 is complete. Do not start Phase 15 (hybrid/fallback between detection providers) until
explicitly requested.

## Blockers

None.

## Decisions

[ADR 0013](../decisions/0013-azure-document-intelligence-provider.md) — Azure as a second
provider. [ADR 0014](../decisions/0014-batched-translation-and-request-duration.md) — batched
translation and the request-duration ceiling.
