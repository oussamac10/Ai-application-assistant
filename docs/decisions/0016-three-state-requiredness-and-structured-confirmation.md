# ADR 0016 — Three-state requiredness and structured summary confirmation

Status: accepted
Date: 2026-07-30
Phase: 16 (stabilization, ahead of hybrid document detection)

## Context

A French employment form could not be finalized:

```
POST /api/form-sessions/{id}/confirm-summary
409  {"detail": "Field 'date_de_d_but_d_emploi' contains invalid value."}
```

The field was empty. The message was wrong about what happened, wrong about
which field mattered, and unactionable — and behind it were two separate
defects that had been reinforcing each other since Phase 15.

**1. A boolean cannot say "the document told us nothing."**

Phase 15 introduced evidence-based requiredness (`app/field_detection/
requiredness.py`) with three states, then immediately threw the third away:
`question_bridge` collapsed it via `Requiredness.blocks_progress` into
`FormField.required: bool`. For a detected form, `unknown` is not an edge case —
it is the overwhelming majority, because most documents mark nothing. The
frontend then read that boolean and rendered an unconditional paragraph:

```tsx
{currentField.required ? t("required") : t("optional")}
```

so every unmarked question was labelled "Optional" — a claim the document had
never made. The product rule is that we never invent information
(`docs/claude/domain-rules.md`); labelling silence is inventing information.

**2. Validation ran on the absence of a value.**

```python
for field in version.fields:
    ans = answers.get(field.id)
    if field.required:
        if not ans or ans.status != "confirmed":
            raise StateConflictError(...)
    if ans:
        if ans.validation_status != "valid":
            raise StateConflictError(f"Field '{field.key}' contains invalid value.")
```

`if ans:` fires for *any* answer record. A skipped question stores
`validation_status="not_checked"` by design, so deliberately skipping an
optional question made the summary permanently unconfirmable — reported as an
invalid value, about a field that had no value at all. And the first `raise`
won, so a user with several problems discovered them one request at a time.

## Decision

### Requiredness is three states, stored, all the way to the client

`FormField.requiredness` (`required | optional | unknown`) is the source of
truth. `FormField.required` stays as a derived boolean so existing callers,
exports and templates keep working, kept consistent by
`forms/services.py::resolve_requiredness`. The richer value always wins when
both are supplied — including against the boolean's historical `True` default,
which is exactly the collapse being removed.

Migration `cae821cb676c` backfills existing rows from that boolean, which is
the only evidence they carry: hand-authored template fields that said
`required = true` genuinely declared themselves required.

The frontend renders a label only for a finding. `unknown` renders **nothing**.

### Requiredness and answer state are independent

`app/answers/states.py` is the single place that answers both questions:

- **requiredness** — what the *document* said. Never inferred from whether an
  answer exists.
- **answer state** — `unreached | unanswered | skipped | answered | invalid`:
  what the *user* did. Never inferred from requiredness.

Only the cross-product decides anything:

| | unreached / unanswered | skipped | answered | invalid |
|---|---|---|---|---|
| required | blocks | blocks | must be confirmed | blocks |
| optional | allowed | allowed | validated | blocks |
| unknown | allowed | allowed | validated | blocks |

A wrong value blocks regardless of requiredness — a bad date is bad on an
optional field too. Absence blocks only where the document demanded something.

### Validators only ever see a submitted value

`submit_answer` refuses a blank outright (422) rather than storing it. A blank
is not an answer and not a skip: storing it would send an empty string into
normalization, the date parser and the AI provider, each of which then reports
something about a value that does not exist. Skipping is an explicit action
with its own endpoint and its own state.

### Confirmation returns data, not a sentence

`SummaryNotConfirmableError` (409) lists every blocking field at once:

```json
{
  "code": "summary_not_confirmable",
  "missing_required_fields": [],
  "invalid_answer_fields": [
    {"field_key": "date_de_d_but_d_emploi", "reason": "invalid_date"}
  ]
}
```

Field **keys** and stable reason codes only. Submitted values, labels and
normalized forms are private and never appear in a response or a log; the
client already knows which field each key is.

### Editing is navigation, not resubmission

Editing from the summary used to re-submit the field's stored answer to
un-confirm it — which meant submitting an empty string for a question that had
none, and became impossible once blanks were refused. `POST
/form-sessions/{id}/fields/{field_id}/reopen` moves the session's position and
withdraws confirmation without touching the value, so a skipped or never
answered question can be edited exactly like an answered one.

## Alternatives rejected

**Treat `unknown` as optional.** Simplest, and the one thing the phase brief
forbids. It is a claim about the document, and the difference is visible: an
admin reviewing a detected form needs to know which fields were *marked*
optional and which were merely unmarked, and an export step may reasonably warn
about the latter while ignoring the former.

**Treat `unknown` as required.** The status quo, and the cause of the bug —
users blocked on questions the form never asked them to answer.

**Keep a single generic 409 and let the client re-derive the reason.** The
client cannot: it does not know which validator ran or why. Re-deriving it would
duplicate backend rules in TypeScript, and they would drift.

**Store a skip as an empty string.** Rejected in Phase 15 and again here: it
cannot be told apart from a question never reached, and it gets validated and
normalized as if it were a value.

## Consequences

- `docs/claude/domain-rules.md`'s "never invent information" now holds for
  requiredness, which was the one place the pipeline was still guessing.
- Progress and completion stay separate from requiredness (Phase 15's
  `totalQuestions` / `answeredQuestions` are unchanged and still correct).
- Counts-only diagnostics (`required_fields`, `unknown_requiredness_fields`,
  `missing_required_fields`, `skipped_fields`, …) make "why is this form stuck?"
  answerable from a log line without any private content in it.
- The three states are carried but not yet *editable*: a per-field admin
  override remains open, as recorded in `TODO.md`.
