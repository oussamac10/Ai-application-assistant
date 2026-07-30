# Current Phase

## Phase

Phase 16 - Hybrid Document Detection

## Branch

`feature/hybrid-document-detection`

## Base

`feature/azure-translator`

## Objective

Route field detection **local-first**, calling Azure Document Intelligence only when a
deterministic quality score says the local result is insufficient — so an ordinary digital PDF
costs nothing and a hard one still works.

The phase opens with a **stabilization pass** that must land, be tested, documented, committed and
manually verified before any routing work begins. That is not preamble: the routing decision is
about what a document actually yielded, and the question model could not previously say what a
document had declared.

## Part 1 — Validation and requiredness stabilization

### The failure that motivated it

```
POST /api/form-sessions/{id}/confirm-summary
409  {"detail": "Field 'date_de_d_but_d_emploi' contains invalid value."}
```

The field was empty. Two root causes:

1. **`if ans:` validated any answer record**, value or not. A skipped question stores
   `validation_status="not_checked"` by design, so skipping an optional question made the summary
   permanently unconfirmable — reported as an *invalid value*, about a field with no value. The
   first `raise` also won, so several problems surfaced one request at a time.
2. **Requiredness was a boolean.** Phase 15 detected three states and then collapsed them, so
   `unknown` — the majority case for a detected form — became `required`, and the frontend
   labelled every unmarked question "Optional", a claim no document had made.

### What was built

- `FormField.requiredness` (`required | optional | unknown`) as the source of truth, with
  `required` kept as a derived legacy boolean; migration `cae821cb676c` backfills existing rows
  from that boolean.
- `app/answers/states.py` — requiredness and answer state (`unreached | unanswered | skipped |
  answered | invalid`) as two independent dimensions, neither inferred from the other. Only the
  cross-product decides anything.
- `confirm_summary` split into separate checks raising `SummaryNotConfirmableError`: a 409
  carrying `missing_required_fields` and `invalid_answer_fields`, each entry a **field key and a
  reason code** — never a submitted value or a label.
- Blank submissions refused (422) rather than stored, so no validator, normalizer or AI call ever
  receives one.
- Skip allowed for `optional` **and** `unknown`; refused only for `required`.
- `POST /form-sessions/{id}/fields/{field_id}/reopen` — editing is navigation, so a skipped or
  never answered question can be edited (the old path re-submitted the stored answer, which meant
  submitting an empty string for a question that had none).
- Frontend: no requiredness label for `unknown`; the summary distinguishes Skipped / Not answered
  / Missing required answer / Answer needs attention, every row editable; a rejected confirmation
  marks every field the backend named.
- Counts-only confirmation diagnostics.

Decisions and rejected alternatives:
[ADR 0016](../decisions/0016-three-state-requiredness-and-structured-confirmation.md).

## Part 2 — Hybrid local-first detection

`FIELD_DETECTION_PROVIDER=hybrid` runs the local pass on every document, scores it
deterministically (`app/field_detection/quality.py`: field count, label quality, input evidence
and provider confidence, weighted — no model, no network call), and calls Azure only below
`HYBRID_LOCAL_QUALITY_THRESHOLD`.

Escalation can only improve the answer: a failure, a missing configuration, or an Azure result
scoring no higher all serve the local result. `HYBRID_MAX_ESCALATION_PAGES` blocks long documents
regardless of score, checked before quality so the reported reason is the useful one. Cost
accounting follows the engine that actually answered, and `hybrid` deliberately does not fail
startup without Azure credentials — unconfigured means "cannot escalate".

Decisions: [ADR 0017](../decisions/0017-hybrid-local-first-field-detection.md).

## Out of scope

- Per-field admin override of requiredness (carried)
- Per-tenant/per-period spend caps and escalation-rate dashboards (Phase 23)
- Background jobs / progress polling (Phase 20)

## Status

Both parts implemented and verified, committed separately.

Backend **891 passed**, ruff / `ruff format --check` / mypy clean (159 files), migration
`cae821cb676c` round-trips. Frontend **157 passed**, lint and typecheck clean.

Live under `hybrid`: the German rental contract scores 0.826 and is served locally with **no
Azure call**; a one-field PDF escalates and has its equal-scoring Azure result discarded
(`azure_not_better`). Both guards observed in production, not only in tests.
