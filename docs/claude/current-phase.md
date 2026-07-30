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

Not started. Attempt local detection first, score extraction quality deterministically, call Azure
only when the local result is insufficient, preserve cached Azure results, record fallback
reasons, enforce page and cost limits, and compare both providers against fixed fixtures. AI never
decides provider spending.

## Out of scope

- Per-field admin override of requiredness (carried)
- Background jobs / progress polling (Phase 20)
- Billing or quota enforcement — cost *limits* only, no metering product

## Status

Part 1 implemented and verified. Part 2 not started.

Backend **859 passed**, ruff / `ruff format --check` / mypy clean (157 files), migration
`cae821cb676c` round-trips. Frontend **157 passed**, lint and typecheck clean.
