# ADR 0013 — Azure Document Intelligence as a Second Detection Provider

**Status:** Accepted
**Phase:** 14 — Azure Document Intelligence Provider
**Date:** 2026-07-30

---

## Context

Phase 11 introduced a `FieldDetectionProvider` protocol with a deterministic, local
rules-based implementation, and Phase 13 invested heavily in making that local detector
handle real German public-sector forms (Unicode dotted leaders, underscore runs,
sentence-embedded whitespace blanks, party/section context for repeated labels).

That local detector is good but inherently limited: it only sees what a PDF's text layer
already contains, in the geometry the exporter happened to produce. A hosted document-AI
service can additionally supply real key/value pairing, selection-mark state, and table
structure — and can read scanned pages without a separate OCR step.

Phase 14 adds Azure Document Intelligence as a **second, opt-in** provider. It does not
replace the local one, and it deliberately does **not** implement fallback between the two
(that is Phase 15).

---

## Decisions

### 1. REST API over the `azure-ai-documentintelligence` SDK

The repository already depends on `httpx` (the Ollama provider uses it), so calling the
Analyze REST endpoint directly adds **no new dependency**. The project's dependency rules
require justifying every addition and prefer an existing capability, and the SDK's value
here — a typed wrapper plus its own polling loop — is exactly the part we want under our
own control, because the timeout and bounded-retry budget is a product requirement rather
than a library default. It also makes deterministic testing a matter of stubbing `httpx`,
identical to how `tests/ai/test_ollama_provider.py` already works, so no test ever needs
network access or credentials.

The API version is configuration (`AZURE_DOCUMENT_INTELLIGENCE_API_VERSION`, default
`2024-11-30`) rather than a pinned constant, so the endpoint can be moved forward without
a code change.

### 2. Azure words are fed through the *existing* local text passes

The provider does not reimplement field-finding. It converts Azure `words` and
`selectionMarks` into the same `DetectionToken` shape the local provider consumes and calls
`LocalFieldDetectionProvider.detect_from_tokens()`.

This is the single most valuable decision in the phase: every Phase 13 behaviour — blank-run
recognition, label-above-blank-line, sentence-embedded German date/currency blanks,
party/`§`-section context that keeps landlord and tenant distinct, prose/heading/footnote
exclusion — applies to Azure output for free, and can never drift between providers. Azure
then *adds* what only it knows: `keyValuePairs`, emitted first so the shared
`deduplicate_candidates` prefers Azure's explicit pairing over layout inference.

### 3. Azure's confidence is an input, never a decision

Phase 13's deterministic routing (`app/field_detection/confidence.py`) is untouched. Azure's
per-element confidence feeds a candidate's `confidence` value, but the auto-confirm and
clarification thresholds, the "unknown type never auto-confirms" and "choice field without
options never auto-confirms" rules, ownership, and authorization all remain local, testable
decisions. A hosted service is never allowed to decide whether a user is asked a question.

### 4. Coordinates are converted eagerly into PDF point space

Azure reports polygons in the page's own `unit` (`inch` or `pixel`), and some models emit
normalized 0–1 coordinates. All three are converted at the boundary into the top-left-origin
PDF point space the rest of the pipeline (review UI, mapping, future export) already uses,
so no downstream consumer needs to know which provider produced a box. A missing, malformed,
or degenerate polygon yields `None` rather than a guessed rectangle — geometry we do not
have must not be invented.

Pixel pages need the PDF's own page size to be convertible at all; when that is unavailable
the conversion assumes the common 96 DPI rendering rather than silently emitting
wrong-by-orders-of-magnitude geometry.

### 5. Caching is fingerprinted on (checksum, provider, model, analysis version)

`FieldDetectionResult` previously keyed reuse on `(source_document_id, analysis_version)`
alone. With more than one provider that is unsafe: switching `FIELD_DETECTION_PROVIDER`
would silently serve the *other* provider's fields. A `detection_fingerprint` column now
gates reuse, and because a paid provider is involved this doubles as cost control — an
unchanged document/configuration never triggers a second Azure call, and the cache hit is
recorded with `served_from_cache=True`.

### 6. Usage metadata lives in a provider-agnostic table

`provider_usage_records` records what a provider was asked to do (provider, model, page
count, duration, success, error code, provider request id, cache hit) — never document
content. It is deliberately not named `azure_*` so Phase 15+ providers reuse it, and it
carries a nullable `estimated_cost` left unpopulated until Phase 18 defines real pricing.
Recording failures is wrapped so usage accounting can never fail a user's document.

### 7. Errors are mapped to safe internal codes at the boundary

`AzureDocumentIntelligenceError` carries one of six fixed codes
(`azure_not_configured`, `azure_authentication_failed`, `azure_rate_limited`,
`azure_timeout`, `azure_invalid_response`, `azure_processing_failed`) plus Azure's request
id for internal diagnostics. `FieldDetectionService` records it, logs the code and request
id, and re-raises the ordinary `FieldDetectionValidationError("field_detection_failed")`
that the orchestration layer already turns into a generic user message. The word "Azure",
the endpoint, the API key, and any response body never reach a user or a log line.

---

## Consequences

- Operators can switch providers with one environment variable, and switching invalidates
  the cache rather than serving stale cross-provider results.
- The local provider remains the default, so no existing deployment changes behaviour and
  no one is required to hold Azure credentials.
- Sending a document to Azure means sending it to a third party. That is a material privacy
  change, so it is off by default, requires two explicit settings
  (`AZURE_DOCUMENT_INTELLIGENCE_ENABLED` *and* `FIELD_DETECTION_PROVIDER=azure`), and is
  documented in `docs/privacy.md`.
- Because Azure words are re-run through the local text passes, a future improvement to
  those passes automatically improves the Azure path too — but equally, a regression there
  affects both providers. The shared behaviour is covered by both providers' test suites.
- No fallback exists yet: if Azure fails, the document fails with the generic processing
  error. Phase 15 adds hybrid behaviour.
