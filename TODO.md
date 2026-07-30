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
15. Azure Translator Integration

## Current Task

Phase 16 — Hybrid Document Detection. Branch `feature/hybrid-document-detection`, based on
`feature/azure-translator`.

**Status: Part 1 (validation and requiredness stabilization) complete. Part 2 (hybrid
local-first routing) not started.**

Phase doc: `docs/phases/phase-16-hybrid-document-detection.md`.
Decisions: [ADR 0016](docs/decisions/0016-three-state-requiredness-and-structured-confirmation.md).

---

## Part 1 — Validation and requiredness stabilization

### The reported failure

```
POST /api/form-sessions/{session_id}/confirm-summary
409  {"detail": "Field 'date_de_d_but_d_emploi' contains invalid value."}
```

The field was left empty. Two independent root causes met in one line of `confirm_summary`:

| Symptom | Cause |
|---|---|
| An empty question reported as "contains invalid value" | `if ans:` validated **any** answer record, value or not. A skip stores `validation_status="not_checked"` by design, so a skipped question blocked the summary forever. |
| Questions the form never marked blocked progress | Requiredness was a boolean. Phase 15 detected three states and `question_bridge` collapsed them, so `unknown` became `required`. |
| Every unmarked question labelled "Optional" | The frontend rendered an unconditional paragraph from the same boolean — a claim the document never made. |
| Problems surfaced one at a time | The first `raise` won. |
| A skipped question could not be edited from the summary | "Edit" re-submitted the stored answer, which for a skipped question meant submitting an empty string. |

### Implementation checklist

- [x] `FormField.requiredness` (`required | optional | unknown`) as the source of truth;
      `required` kept as a derived legacy boolean, consistent on every write.
- [x] Migration `cae821cb676c`, backfilling existing rows from the legacy boolean; round-trips.
- [x] `resolve_requiredness()` — the richer value always wins, including over the boolean's
      historical `True` default.
- [x] `_resolve_requiredness()` in `question_bridge` writes the real three-state value.
- [x] `app/answers/states.py` — requiredness and answer state as two independent dimensions.
- [x] Answer states: `unreached | unanswered | skipped | answered | invalid`, reported as
      `answerState`.
- [x] `confirm_summary` split into separate checks; `SummaryNotConfirmableError` lists every
      blocking field at once.
- [x] Structured 409 body: `code`, `missing_required_fields`, `invalid_answer_fields` — field
      keys and reason codes only, never a value or a label.
- [x] Blank submissions refused (422) rather than stored; no validator, normalizer or AI call
      ever receives one.
- [x] Skip allowed for `optional` **and** `unknown`, refused only for `required`.
- [x] `POST /form-sessions/{id}/fields/{field_id}/reopen` — editing is navigation, not
      resubmission.
- [x] `get_current_field` honours a deliberately moved position (skip, reopen) instead of always
      jumping to the first incomplete required field.
- [x] Frontend: no requiredness label for `unknown`; Skip shown for `optional` and `unknown` and
      never tied to the input value.
- [x] Summary distinguishes Skipped / Not answered / Missing required answer / Answer needs
      attention; every row editable.
- [x] A rejected confirmation marks every field the backend named.
- [x] A response without `requiredness` is read as `unknown`, never `optional`.
- [x] `notAnswered`, `invalidAnswer`, `blockedByFields` added to en/de/fr/ar.
- [x] Counts-only confirmation diagnostics.
- [x] Leading asterisk (`* Nom`) recognised alongside trailing, per the brief's evidence list.
- [x] ADR 0016, phase doc, architecture, domain rules, security, form/answer models, README.

### Tests added

| File | Count | Covers |
|---|---|---|
| `tests/answers/test_confirm_summary_requiredness.py` | 22 | the six reported `date_de_d_but_d_emploi` cases, the requiredness x answer-state grid, blank refusal, privacy of the structured error, progress with skips, reopen |
| `tests/field_detection/test_requiredness_persistence.py` | 16 | detection -> three states, boolean/state consistency, persistence |
| `tests/field_detection/test_requiredness.py` | +9 | leading asterisk, `Required`/`mandatory`/`obligatoire`/`requis`/`إلزامي`, semantic importance never producing `required` |
| `guided-session-requiredness.test.tsx` | 8 | label per state, no label for `unknown`, Skip per state, Skip never tied to input |
| `summary-answer-states.test.tsx` | 7 | Skipped / Not answered / Missing required, asterisk only for a finding, editing a skipped row, blocking-field marking |
| `reopen-and-summary-errors.test.ts` | 4 | reopen posts no body, structured 409 parsing, malformed entries ignored |
| `e2e/requiredness-and-skip-flow.spec.ts` | 4 | unmarked question unlabelled and skippable, explicit optional still labelled, empty date does not 409, invalid date reported on the field |

### Quality gates (run sequentially, never pytest and Playwright at once)

| Gate | Result |
|---|---|
| backend `pytest` | **859 passed** (was 809) |
| `ruff check .` | All checks passed |
| `ruff format --check` (changed files) | clean |
| `mypy app` | Success, 157 source files |
| frontend `npm test` | **157 passed** (was 138), 22 files |
| `npm run lint` | no warnings or errors |
| `npm run typecheck` | clean |
| migration `cae821cb676c` | upgrade / downgrade / upgrade all clean |
| Playwright (full suite) | **30 passed, 1 flaky, 3 failed** — see below |
| Playwright (`requiredness-and-skip-flow.spec.ts` alone) | **4 passed** (21.7 s) |

Full-suite failures, all environmental, pre-existing, or since fixed:

- `guided-flow.spec.ts` — pre-existing default-tab gap since Phase 9.
- `dynamic-field-detection-flow.spec.ts:114`, plus the flaky upload in the new requiredness
  spec — Azure Document Intelligence **F0 rate limiting**, confirmed in the backend log
  (`code=azure_rate_limited`, `HTTP 429 Too Many Requests`) after the suite uploads several PDFs
  in quick succession. The new spec's per-test budget was raised to 150 s so a rate-limit retry
  fits inside it; run alone after a pause, all four pass.
- The new spec's fourth test was a **flaw in the test, not the product**: it tried to type
  `"pas une date"` into a field that renders as a native `<input type="date">`, which refuses a
  malformed value before the app sees it. An invalid date is not reachable through this UI, so
  it is asserted where it *is* reachable — `test_case_5_invalid_date_reports_invalid_date`
  checks the API returns `{"field_key": "date_de_d_but_d_emploi", "reason": "invalid_date"}` —
  and the E2E test now covers the reported failure's other half: an empty date is never treated
  as an answer, Continue stays gated, and Skip is offered.

A first run of the whole suite reported 32 failures including trivial landing-page assertions.
That was **not** a regression: `playwright.config.ts` defaults to port 3000 while the compose
frontend publishes 3003. `PLAYWRIGHT_BASE_URL=http://localhost:3003` is required.

### Live verification (running stack, detected French document)

```
current-field   key=nom_de_famille  required=False  requiredness=unknown
blank submit    HTTP 422  "An answer cannot be empty. Skip the question instead…"
confirm-summary HTTP 409  {"code": "summary_not_confirmable",
                           "missing_required_fields": [{"field_key": "signature",
                                                        "reason": "missing_required"}],
                           "invalid_answer_fields": []}
```

`nom_de_famille` is `unknown` and does not block; only `signature` — the one field the document
marked with an asterisk — does, and it is named by key with a reason code rather than by a
sentence about the wrong field. Skipping every non-required question then confirms with **HTTP
200**, which is the exact scenario that used to return the reported 409.

---

## Part 2 — Hybrid local-first detection (not started)

- [ ] Attempt local field detection first.
- [ ] Deterministic extraction-quality score (no AI, no invented confidence).
- [ ] Call Azure only when local quality is insufficient.
- [ ] Preserve cached Azure results across the routing change.
- [ ] Record fallback reasons.
- [ ] Enforce page and cost limits; AI never decides provider spending.
- [ ] Compare local and Azure output against fixed fixtures.

---

## Carried Deferred Items

- Requiredness still has no per-field admin override. The three states are carried end to end
  and reviewable, but not editable.
- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10).
- Pre-existing Ruff formatting exceptions under `app/documents/*` and `tests/documents/`.
- Preparation is still synchronous; background jobs with progress polling remain Phase 20.
- The translation cache is process-local and dropped on restart.
- A long wrapped checklist splits into one question per row (never merged).
- Azure mistranslates some isolated one-word options (`Français` -> `الإنجليزية`), verified
  against the provider with correct ids; stable values are unaffected.
- Arabic field *detection* quality with RTL layout — a Phase 13/14 heuristics limitation.
- With Ollama selected, a German document in an English interface is still not translated: the
  local model cannot detect a source language. Only Azure resolves this.
- The French employment form used in live testing is not committed (it is a real document);
  `e2e/requiredness-and-skip-flow.spec.ts` builds a synthetic equivalent carrying the three
  requiredness cases.

## Operational notes

- Playwright needs `PLAYWRIGHT_BASE_URL=http://localhost:3003` — the compose frontend publishes
  3003, while `playwright.config.ts` defaults to 3000. Without it every spec fails on page load.
- `docker compose restart` does **not** re-read `.env`; use `up -d --force-recreate`.
- Never run backend pytest and Playwright against the same dev database at once — pytest
  `TRUNCATE`s `form_templates` and wipes the `basic-registration` fixture mid-run. Reseed with
  `docker compose exec backend python -m app.commands.load_fixture`.
