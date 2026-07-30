# Phase 16 — Hybrid Document Detection

Branch `feature/hybrid-document-detection`, based on `feature/azure-translator`.

The phase objective is local-first field detection with Azure as a fallback. It
opens with a **stabilization pass** on validation and requiredness, because the
routing work would otherwise be built on a question model that could not say
what a document had actually declared.

---

## Part 1 — Validation and requiredness stabilization

Rationale and rejected alternatives:
[ADR 0016](../decisions/0016-three-state-requiredness-and-structured-confirmation.md).

### The reported failure

```
POST /api/form-sessions/{id}/confirm-summary
409  {"detail": "Field 'date_de_d_but_d_emploi' contains invalid value."}
```

The field was empty. Two root causes met in one line of `confirm_summary`:

| Cause | Effect |
|---|---|
| `if ans:` validated any answer record, value or not | A skipped question (`validation_status="not_checked"` by design) blocked the summary forever, reported as an *invalid value* |
| Requiredness was a boolean, so `unknown` became `required` | Users were blocked on questions the document never marked; the UI labelled every one of them "Optional" |

### What changed

```
app/answers/states.py          requiredness x answer state, decided in one place
app/answers/errors.py          SummaryNotConfirmableError — keys and reason codes
app/forms/models.py            FormField.requiredness (required|optional|unknown)
app/forms/services.py          resolve_requiredness() keeps the boolean derived
migrations/…cae821cb676c       column + backfill from the legacy boolean
```

**Answer states**, distinct on purpose:

| state | meaning |
|---|---|
| `unreached` | no answer record |
| `unanswered` | a record exists with no value |
| `skipped` | explicit skip; `status="skipped"`, null values |
| `answered` | a non-empty submitted value |
| `invalid` | a submitted value that failed validation |

**What blocks confirmation:**

| | unreached / unanswered | skipped | answered | invalid |
|---|---|---|---|---|
| `required` | blocks | blocks | must be confirmed | blocks |
| `optional` | allowed | allowed | validated | blocks |
| `unknown` | allowed | allowed | validated | blocks |

**Structured 409**, with every blocking field at once:

```json
{
  "code": "summary_not_confirmable",
  "missing_required_fields": [{"field_key": "signature", "reason": "declaration_not_accepted"}],
  "invalid_answer_fields": [{"field_key": "date_de_d_but_d_emploi", "reason": "invalid_date"}]
}
```

Reason codes: `missing_required`, `declaration_not_accepted`, `not_confirmed`,
`required_question_skipped`, `invalid_date`, `invalid_email`, `invalid_phone`,
`invalid_number`, `invalid_currency`, `invalid_country`, `invalid_iban`,
`invalid_boolean`, `invalid_choice`, `needs_clarification`, `invalid_value`.
Never a submitted value, a label, or a normalized form of either.

**Blank submissions are refused** (422) rather than stored, so no validator,
normalizer or AI call ever receives one. An empty string is not a skip.

**Skip** is allowed for `optional` *and* `unknown`, refused only for
`required`.

**Editing is navigation**: `POST /form-sessions/{id}/fields/{field_id}/reopen`
moves the position and withdraws confirmation without touching the stored value,
so a skipped or never answered question is editable. The old approach
re-submitted the existing answer, which meant submitting an empty string for a
question that had none.

### Frontend

- No requiredness label at all for `unknown`; "Required"/"Optional" only for a
  real finding. The unconditional `data-testid="requiredness"` paragraph is
  gone.
- Skip is offered for `optional` and `unknown`, and is never tied to the input
  value.
- The summary distinguishes **Skipped** / **Not answered** / **Missing required
  answer** / **Answer needs attention**, and every row stays editable.
- A rejected confirmation marks every field the backend named, rather than
  showing one generic message.
- A response without `requiredness` (an older backend) is read as `unknown`,
  never as `optional`.

### Diagnostics

One line per confirmation attempt, counts only — no label, key, value or token:

```
Summary confirmation check: session=… confirmable=False required_fields=1
optional_fields=1 unknown_requiredness_fields=1 missing_required_fields=1
unanswered_optional_fields=1 unanswered_unknown_fields=1 skipped_fields=0
invalid_answered_fields=0
```

### Verification

| Gate | Result |
|---|---|
| backend `pytest` | **859 passed** (was 809) |
| `ruff check` | clean |
| `ruff format --check` | clean on changed files |
| `mypy app` | clean, 157 files |
| frontend `npm test` | **157 passed** (was 138) |
| `npm run lint` / `typecheck` | clean |
| migration `cae821cb676c` | round-trips |
| Playwright (full suite) | **30 passed, 1 flaky, 3 failed** — `guided-flow.spec.ts` (pre-existing since Phase 9) and Azure Document Intelligence F0 rate limiting (`azure_rate_limited`, HTTP 429), confirmed in the backend log |
| Playwright (`requiredness-and-skip-flow.spec.ts` alone) | **4 passed** (21.7 s) |

An invalid date is not reachable through this UI — the field renders as a native
`<input type="date">`, which refuses a malformed value before the app sees it. That path is
asserted at the API level instead
(`test_case_5_invalid_date_reports_invalid_date`); the E2E test covers the reported failure's
other half, that an empty date is never treated as an answer.

Playwright needs `PLAYWRIGHT_BASE_URL=http://localhost:3003`: the config defaults to 3000 while
the compose frontend publishes 3003. Without it every spec fails on page load.

### Live verification (running stack, detected French document)

```
current-field   key=nom_de_famille  required=False  requiredness=unknown
blank submit    HTTP 422  "An answer cannot be empty. Skip the question instead…"
confirm-summary HTTP 409  {"code": "summary_not_confirmable",
                           "missing_required_fields": [{"field_key": "signature",
                                                        "reason": "missing_required"}],
                           "invalid_answer_fields": []}
```

`nom_de_famille` is `unknown` and no longer blocks; only `signature` — the one field the document
marked with an asterisk — does. Skipping every non-required question then confirms with HTTP 200,
which is precisely the scenario that produced the reported 409.

New tests: `tests/answers/test_confirm_summary_requiredness.py` (22, including
the six reported `date_de_d_but_d_emploi` cases),
`tests/field_detection/test_requiredness_persistence.py` (16),
requiredness-evidence additions in `tests/field_detection/test_requiredness.py`,
and on the frontend `guided-session-requiredness.test.tsx` (8),
`summary-answer-states.test.tsx` (7), `reopen-and-summary-errors.test.ts` (4),
plus `e2e/requiredness-and-skip-flow.spec.ts`.

---

## Part 2 — Hybrid local-first detection

Not started. Begins only once Part 1 is committed and manually verified.

Planned: attempt local detection first, score extraction quality
deterministically, call Azure only when the local result is insufficient,
preserve cached Azure results, record fallback reasons, enforce page and cost
limits, and compare both providers against fixed fixtures. No AI decides
provider spending.
