# ADR 0014 — Batched translation, and who owns the request-duration ceiling

- Status: Accepted
- Date: 2026-07-30
- Phase: 14 (Azure Document Intelligence Provider)

## Context

With Azure field detection working correctly (24 usable fields, 24 generated questions on the
reference German rental contract), users still saw a processing error. Measured through the
frontend proxy exactly as the browser calls it:

```
POST /api/source-documents/{id}/prepare-questions
  -> http_status=500  total_time=30.08s   body: "Internal Server Error" (plain text)
```

Two separate defects, one visible symptom.

**1. Nothing enforced a duration budget, and the layer that gave up first reported it as a
server error.** The body was not the API's `{code, message, stage}` JSON, and the frontend
container logged `Failed to proxy … Error: socket hang up`. Next.js's rewrite proxy abandons an
upstream request after 30 s by default. The backend was unaffected and went on to finish
successfully — so the user was shown a failure for a document that worked, and a session that
existed was never reached.

**2. Question generation cost one AI call per text.** `question_bridge` translated each field
label, and each choice option, in its own sequential `translate_text` call:

| | measured |
|---|---|
| Ollama calls | 28 |
| total duration (detection cached) | 41.4 s |

41 s against a 30 s ceiling. The margin was negative, so the failure was not intermittent.

## Decision

### Batch, deduplicate, and cache translation — `app/ai/batch_translation.py`

Every text a document needs is collected before any field is built, then resolved cheapest-first:
deduplicate, process-local LRU cache, approved catalog translations, and only then the provider,
in bounded chunks. `AIProvider` gained `translate_output_batch`.

Three properties were deliberately designed in rather than left to the model:

- **Results are keyed by request id, never by response position.** A provider that reorders,
  repeats, or drops entries cannot move one field's translation onto another field. This is the
  only failure mode here that would silently corrupt user-facing data rather than merely cost
  time, so it is a mapping invariant, not a validation step.
- **Entries are validated one at a time.** Validating the whole response at once was tried first
  and was wrong: a real local-model reply contained `"id": ": 1"` among three valid entries, and
  strict whole-response validation discarded all four. Now only the malformed entry is dropped.
- **Recovery is per item.** A missing entry falls back to a single-text call for that text alone;
  if that also fails, the source text is used and recorded as untranslated (and *not* cached, so
  a later run retries). A document is never blocked by a translation failure.

`TextTranslation` gained an explicit `succeeded` flag. Inferring failure by comparing input to
output was wrong — a legitimate translation is often identical to its source (a German option
label into German, `IBAN`, a proper noun), which was being counted and logged as a failure.

### Bounded concurrency, because batching alone was not enough

Batching cut calls 28 → 4 but wall time only 41 s → ~48 s of translation: three sequential ~15 s
generations still dominate. Chunks are independent, so they run concurrently behind a semaphore
(`AI_TRANSLATION_CONCURRENCY`, default 3). The bound is the point — a single local Ollama instance
queues work beyond its own parallelism, so unbounded fan-out converts latency into timeouts.

### The proxy ceiling is raised, and the frontend stops trusting it

`experimental.proxyTimeout = 180_000` in `next.config.js`. Preparation is synchronous by design in
this phase; moving it to a background job with progress polling is Phase 17, and pretending the
work fits in 30 s would just relocate the same failure.

Because an intermediary can still drop a slow response, the frontend now treats a *bare* gateway
failure (transport error, 502/504, or a 500 with no application error code) as "still working" and
re-issues the request, bounded to two extra attempts. A real backend error always carries an error
code and is never retried. This is safe only because `prepare-questions` is idempotent: a repeat
call reuses the session it already created — measured at 0.09 s with zero AI calls.

### Frontend state cannot go stale

Concurrent `prepareQuestions` calls for the same document share one in-flight promise. Each
processing run carries a generation id and may only write state while it is still the current run,
so a superseded attempt's late error cannot overwrite a newer success. A successful result always
clears any previous error.

### Structured timing logs

One line per request attributing duration to a stage — counts and durations only, never document
text, labels, answers, or credentials:

```
Azure detect timing: azure_duration=8.77s normalization_duration=0.01s candidates=24
Question generation result: ... translation_duration=34.27s unique_texts=28 cache_hits=0
    catalog_hits=0 batch_calls=3 fallback_calls=1 ollama_call_count=4 untranslated=0
prepare-questions timing: ... ocr_duration=0.00s detection_duration=8.90s
    question_resolution_duration=34.88s total_duration=43.80s status=ready questions=24
```

## Consequences

Measured on the reference PDF, fresh upload each time, through the proxy:

| | before | after |
|---|---|---|
| HTTP status | 500 | 200 |
| total duration | 30.1 s (abandoned) | 43.8 s (completed) |
| Ollama calls | 28 | 4 |
| generated questions | 24 (never delivered) | 24 |
| repeat request | — | 0.09 s, 0 AI calls, session reused |

Translation is still 34 s of the 43.8 s, and that remaining time is Ollama's own generation, not
orchestration: three concurrent 12-item requests against one local instance that serializes them.
Reducing it further means a faster model, a provider with real parallelism, or not translating at
all — see below.

Accepted trade-offs and known limitations:

- **The request is still long.** 43.8 s is under the ceiling but is not a good experience. The
  real fix is Phase 17 (background jobs + progress polling); this ADR makes the synchronous path
  honest rather than pretending it is fast.
- **Most of this translation is unnecessary.** The reference document is German, but detected text
  is *assumed* to be `_DEFAULT_SOURCE_LANGUAGE` (`en`) because field detection performs no
  document-language detection. Its German labels are therefore sent on an `en → de` round trip
  that mostly returns them unchanged. Detecting the document's language would eliminate most of
  the cost. Deliberately out of scope here: it changes detection behaviour.
- **The translation cache is process-local and not persisted.** Two backend workers each keep
  their own; a restart drops it. Adequate for a convenience cache, and no user data is stored in
  it.
- **`proxyTimeout` is an `experimental` Next.js option.** It is the documented knob for this in
  Next 14, but it is not a stability guarantee.
