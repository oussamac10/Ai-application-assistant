# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Phase 16, **both parts**, committed separately as instructed:

- `fix: stabilize optional unknown and required field validation`
- `feat: add hybrid local-first document detection`

Part 1 is described in full below. Part 2 adds `FIELD_DETECTION_PROVIDER=hybrid`: the local pass
runs on every document, its output is scored deterministically
(`app/field_detection/quality.py` — field count, label quality, input evidence and the provider's
own confidence, weighted; no model, no network call), and Azure is called only below
`HYBRID_LOCAL_QUALITY_THRESHOLD`. Escalation can only improve the answer — a failure, a missing
configuration, or an Azure result scoring no higher all serve the local result — and
`HYBRID_MAX_ESCALATION_PAGES` blocks long documents regardless of score.

Live under `hybrid`, both guards fired in production rather than only in tests:

```
used=local reason=local_sufficient  pages=3 local_score=0.826 local_fields=19   (Azure never called)
used=local reason=azure_not_better  pages=1 local_score=0.482 azure_score=0.482
```

`.env` was restored to `FIELD_DETECTION_PROVIDER=azure` afterwards — switching the deployment
default to `hybrid` is an operational decision, not one this work should make silently.
See [ADR 0017](../decisions/0017-hybrid-local-first-field-detection.md).

## What was actually wrong

```
POST /api/form-sessions/{id}/confirm-summary
409  {"detail": "Field 'date_de_d_but_d_emploi' contains invalid value."}
```

The field was empty. Every clause of that response was wrong, and two independent defects met in
one line of `confirm_summary`:

```python
if ans:
    if ans.validation_status != "valid":
        raise StateConflictError(f"Field '{field.key}' contains invalid value.")
```

1. **It ran on the absence of a value.** `if ans:` fires for any answer record. A skip stores
   `validation_status="not_checked"` *by design*, so deliberately skipping an optional question
   made the summary permanently unconfirmable — reported as an invalid value, about a field that
   had none.
2. **Requiredness was a boolean.** Phase 15 built three-state detection
   (`app/field_detection/requiredness.py`) and then discarded the third state:
   `question_bridge` collapsed it through `blocks_progress` into `FormField.required: bool`. For
   a detected form `unknown` is the *majority* case, so most questions became required. The
   frontend read the same boolean and rendered an unconditional paragraph — labelling every
   unmarked question "Optional", a claim no document had made.
3. The first `raise` won, so a user with several problems found them one request at a time.
4. Editing from the summary re-submitted the field's stored answer to un-confirm it, which meant
   submitting an empty string for a question that had none — so skipped and unanswered questions
   were not editable at all.

## What was built

- **`FormField.requiredness`** (`required | optional | unknown`) as the source of truth;
  `required` stays as a derived legacy boolean, kept consistent by
  `forms/services.py::resolve_requiredness`. Migration `cae821cb676c` backfills existing rows
  from that boolean (the only evidence they carry) and round-trips.
- **`app/answers/states.py`** — requiredness (what the *document* said) and answer state
  (`unreached | unanswered | skipped | answered | invalid`, what the *user* did) as two
  independent dimensions. Neither is inferred from the other; only the cross-product decides.
- **`app/answers/errors.py`** — `SummaryNotConfirmableError`, a 409 listing every blocking field
  as `{field_key, reason}`. Keys and stable reason codes only; a test asserts no submitted value
  or label appears.
- **Blank submissions refused** (422) rather than stored, so nothing null, blank, skipped or
  unreached reaches a validator, normalizer or the AI provider.
- **Skip** allowed for `optional` *and* `unknown`, refused only for `required`.
- **`POST /form-sessions/{id}/fields/{field_id}/reopen`** — editing is navigation. It moves the
  position and withdraws confirmation without touching the value.
- **`get_current_field`** now honours a deliberately moved position (skip, reopen) instead of
  always jumping to the first incomplete required field, which would have undone both.
- **Frontend** — no requiredness label at all for `unknown`; Skip for `optional` and `unknown`,
  never tied to the input value; the summary distinguishes Skipped / Not answered / Missing
  required answer / Answer needs attention with every row editable; a rejected confirmation marks
  every field the backend named. A response missing `requiredness` is read as `unknown`.
- **Counts-only diagnostics** per confirmation attempt.
- A leading asterisk (`* Nom`) is now recognised alongside a trailing one, per the brief's
  evidence list — the regex was anchored to the end only.

## Verification

Backend **859 passed** (was 809), ruff clean, `ruff format --check` clean on changed files, mypy
clean (157 files), migration `cae821cb676c` round-trips. Frontend **157 passed** (was 138), lint
and typecheck clean.

Playwright **30 passed, 1 flaky, 3 failed** — `guided-flow.spec.ts` (pre-existing since Phase 9)
plus Azure Document Intelligence F0 rate limiting, confirmed in the backend log as
`code=azure_rate_limited` / `HTTP 429 Too Many Requests` after several uploads in quick
succession. The new `requiredness-and-skip-flow.spec.ts` run alone after a pause: **4 passed**.

Its fourth test was originally a flaw in the *test*: it tried to type `"pas une date"` into a
field that renders as a native `<input type="date">`, which refuses a malformed value before the
app sees it. An invalid date is unreachable through this UI, so it is asserted at the API level
(`test_case_5_invalid_date_reports_invalid_date`) and the E2E test now covers the other half of
the reported failure — an empty date is never treated as an answer.

Live on the running stack against a detected French document: `nom_de_famille` reports
`requiredness=unknown` and no longer blocks; a blank submission returns 422; `confirm-summary`
returns the structured 409 naming only `signature` (the one asterisk-marked field) with
`reason=missing_required`; skipping every non-required question then confirms with HTTP 200 —
the exact scenario that produced the reported failure.

New tests: `tests/answers/test_confirm_summary_requiredness.py` (22, including the six reported
`date_de_d_but_d_emploi` cases), `tests/field_detection/test_requiredness_persistence.py` (16),
nine more evidence cases in `tests/field_detection/test_requiredness.py`, and on the frontend
`guided-session-requiredness.test.tsx` (8), `summary-answer-states.test.tsx` (7),
`reopen-and-summary-errors.test.ts` (4), plus `e2e/requiredness-and-skip-flow.spec.ts`.

## Operational gotchas worth remembering

- **Playwright needs `PLAYWRIGHT_BASE_URL=http://localhost:3003`.** The compose frontend
  publishes 3003; `playwright.config.ts` defaults to 3000. Without it *every* spec fails on page
  load, including trivial landing-page ones — which looks like a catastrophic regression and is
  not one.
- Never run backend pytest and Playwright against the same dev database at once — pytest
  `TRUNCATE`s `form_templates` and wipes the `basic-registration` fixture mid-run. Reseed with
  `docker compose exec backend python -m app.commands.load_fixture`.
- `docker compose restart` does **not** re-read `.env`; use `up -d --force-recreate`.
- A component test that mocks `next-intl` must return a *stable* function per namespace. The
  summary page lists its translator in an effect's dependency array, so a fresh function each
  render re-runs the effect forever and the page never leaves "loading".

## Known limitations carried forward

- Requiredness has no per-field admin override; the three states are carried and reviewable but
  not editable.
- The French employment form from live testing is not committed (it is a real document); the E2E
  spec builds a synthetic equivalent carrying the three requiredness cases.
- Everything carried from Phase 15 (process-local translation cache, synchronous preparation,
  RTL detection quality, `guided-flow.spec.ts` default-tab gap, Azure F0 rate limiting) is
  unchanged.

## Next action

Phase 16 is complete. Do not start Phase 17 (Administration and Content Review) until explicitly
requested.

Two things are worth doing before then, both operational rather than code:

- Decide whether the deployment default becomes `FIELD_DETECTION_PROVIDER=hybrid`. The evidence
  says yes — the reference document is served free and correctly — but it changes billing
  behaviour, so it is the user's call.
- Per-tenant/per-period spend caps and escalation-rate visibility are deliberately deferred to
  Phase 23; the routing log line is the only view today.

## Decisions

[ADR 0016](../decisions/0016-three-state-requiredness-and-structured-confirmation.md),
[ADR 0017](../decisions/0017-hybrid-local-first-field-detection.md).
