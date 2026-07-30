# ADR 0017 — Hybrid local-first field detection

Status: accepted
Date: 2026-07-30
Phase: 16

## Context

Since Phase 14 the deployment has had to pick one field-detection provider for
every document:

- `FIELD_DETECTION_PROVIDER=local` costs nothing and reads native-text forms
  well, but missed structure on hard documents — the Arabic form that collapsed
  27 candidates into 2 is the reference failure.
- `FIELD_DETECTION_PROVIDER=azure` reads those documents, and bills every
  upload, including the digital PDFs the local pass already handled perfectly.
  The F0 tier's rate limiting made this visible in the E2E suite long before it
  would have shown up on a bill.

Neither is the right default, because which one is right depends on the
document — a fact that is only knowable *after* trying.

## Decision

Add a `hybrid` provider that runs the local pass first, scores its output
deterministically, and calls Azure only when that score says the document was
not read.

### The score is arithmetic, and it is not a confidence

`app/field_detection/quality.py` combines four signals from the candidates
themselves, weighted:

| signal | weight | failure mode it catches |
|---|---|---|
| field count | 0.25 | a form that yielded one or two candidates was not read |
| label quality | 0.40 | placeholder/numeric/one-character labels — geometry found, questions not |
| input evidence | 0.20 | labels with nowhere to write usually mean the layout pass missed the structure |
| mean confidence | 0.15 | the local provider's own per-candidate confidence |

Weighted average rather than all-must-pass: a short form legitimately has few
fields, and any single hard gate would escalate it.

This is deliberately **not** a confidence value about the document.
`docs/claude/domain-rules.md` allows storing a confidence only when it comes
from a provider with documented semantics, and forbids asking a model to invent
one. This is a summary of what an extractor produced, computed with plain code,
no model and no network call — which is also what makes it safe to let it decide
spending, since the same rules say AI never decides provider spending.

### Escalation can only improve the answer

If Azure fails, is not configured, or returns a *lower*-scoring result, the
local result is what the caller gets. A hybrid provider that can fail where the
local provider would have succeeded is a downgrade, so a failed escalation costs
the caller time and nothing else.

### Limits are hard

`HYBRID_MAX_ESCALATION_PAGES` (default 10) blocks escalation regardless of
score, and is checked *before* quality so the reported reason is the fact an
operator needs. A long document is where an automatic hosted call is most
expensive and least likely to be intended.

### Cost accounting follows the engine that answered

The escalated `DetectionResult` keeps Azure's own `provider_name`, so the
persisted row records which engine produced the fields, `_record_provider_success`
meters it, and `last_diagnostics` reports the call's model/request id. When the
local pass answered, `last_diagnostics` is `None` — reporting a stale Azure call
would overstate cost on a document that never made one. Cache hits are metered
against the *stored* provider name for the same reason.

The cache fingerprint includes the Azure model id under `hybrid` as well as
under `azure`: when hybrid does escalate, the answer came from that model, and a
model change must invalidate the result.

### `hybrid` does not require Azure credentials

Unlike `azure`, `hybrid` is not added to the fail-fast configuration check. An
unconfigured Azure is a documented, working mode: it means "cannot escalate",
and the local result is served. Failing startup there would make the cheap
default impossible to deploy without a paid account.

## Alternatives rejected

**Try Azure first and fall back to local on failure.** The obvious inversion,
and it bills every document — the exact cost the phase exists to remove. It also
makes the free provider the *error* path, which is backwards: local is correct
for most documents, not a consolation.

**Route on document metadata (scanned vs digital, page count, language).**
Cheaper — no local pass needed — but it guesses. A digital PDF with a
pathological layout reads badly; a clean scan after OCR reads well. Measuring
the actual output is the only signal that reflects what happened.

**Let the AI provider judge extraction quality.** Explicitly forbidden by
`domain-rules.md`, and it would put a non-deterministic component in charge of
spending. It would also be slower and less reproducible than arithmetic on
counts.

**A single hard gate (e.g. "escalate below N fields").** Simple, and wrong for
short forms — the most common thing a user uploads.

## Consequences

- The default deployment can be `hybrid` without a paid account: it degrades to
  exactly the previous `local` behaviour.
- Measured on the committed German rental contract, the local pass scores
  **0.826** (19 fields, label quality 1.0) — comfortably above the 0.55
  threshold, so a document like it is never billed. The recorded Azure response
  for the same PDF scores identically, because the Azure provider reuses the
  local text passes over Azure's tokens; on this document escalation would have
  bought nothing, which is precisely the case local-first is for.
- `tests/field_detection/test_hybrid_fixture_comparison.py` pins that against
  the real file, so a change to either extractor that would flip a real
  document's routing fails in CI rather than on a bill.
- Escalation is still per-document, not per-request: caching is unchanged and
  lives a layer up.
- Not addressed: a per-tenant or per-period spend cap, and any admin visibility
  into escalation rates beyond the log line. Both belong with the monitoring
  work in Phase 23.
