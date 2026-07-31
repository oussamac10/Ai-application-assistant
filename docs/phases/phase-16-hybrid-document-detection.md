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

Rationale and rejected alternatives:
[ADR 0017](../decisions/0017-hybrid-local-first-field-detection.md).

`FIELD_DETECTION_PROVIDER=hybrid` runs the local pass first and calls Azure only
when the local result was measurably poor.

```
app/field_detection/quality.py            deterministic extraction score
app/field_detection/providers/hybrid.py   the routing itself
```

### The score

Four weighted signals, computed from the candidates themselves — no model, no
network call, and deliberately **not** a confidence about the document:

| signal | weight | catches |
|---|---|---|
| field count | 0.25 | a form that yielded one or two candidates was not read |
| label quality | 0.40 | placeholder/numeric/one-character labels — geometry found, questions not |
| input evidence | 0.20 | labels with nowhere to write |
| mean confidence | 0.15 | the local provider's own per-candidate confidence |

### The decision

```
local pass runs (always)
├── score >= HYBRID_LOCAL_QUALITY_THRESHOLD  -> local_sufficient
├── pages > HYBRID_MAX_ESCALATION_PAGES      -> page_limit_exceeded
├── Azure not configured                     -> azure_not_configured
└── otherwise escalate
    ├── Azure raises                         -> azure_failed        (serve local)
    ├── Azure scores no higher               -> azure_not_better    (serve local)
    └── Azure scores higher                  -> escalated_to_azure  (serve Azure)
```

Every branch serves *something*: a failed escalation costs time and nothing
else. The page limit is checked before quality, so a blocked document reports
the limit rather than its score.

### Configuration

```bash
FIELD_DETECTION_PROVIDER=hybrid
HYBRID_LOCAL_QUALITY_THRESHOLD=0.55   # escalate below this
HYBRID_MAX_ESCALATION_PAGES=10        # hard ceiling, whatever the score
```

`hybrid` does **not** require Azure credentials. Unconfigured means "cannot
escalate", which is a working mode identical to the old `local` provider.

### Cost accounting

An escalated result keeps Azure's own `provider_name`, so it is metered and its
model/request id recorded; a locally-answered document reports no diagnostics at
all, because there was no metered call to describe. Cache hits are metered
against the *stored* provider name. The cache fingerprint includes the Azure
model id under `hybrid` too, so a model change invalidates an escalated result.

### Measured on the committed German rental contract

| | score | fields | label quality | input evidence |
|---|---|---|---|---|
| local | **0.826** | 19 | 1.00 | 0.42 |
| Azure (recorded response, same PDF) | 0.826 | 19 | 1.00 | 0.42 |

Well above the 0.55 threshold, so a document like it is never billed — and the
two providers agree exactly, because the Azure provider reuses the local text
passes over Azure's tokens. On this document escalation would have bought
nothing, which is the case local-first exists for.

### Live verification (`FIELD_DETECTION_PROVIDER=hybrid`, real stack)

```
used=local reason=local_sufficient  pages=3 local_score=0.826 local_fields=19
                                    azure_duration=0.00s          <- never called
used=local reason=azure_not_better  pages=1 local_score=0.482 local_fields=1
                                    azure_score=0.482 azure_fields=1 azure_duration=4.48s
```

Both guards observed in production, not only in tests: the German contract is
served locally with no Azure call at all, and a one-field PDF escalates
correctly but has its equal-scoring Azure result discarded.
`automatic-upload-to-questions-flow.spec.ts` under `hybrid`: 3 passed (14.1 s).

### Tests

`tests/field_detection/test_hybrid_routing.py` (28) covers the score and every
routing branch with a stubbed Azure side.
`tests/field_detection/test_hybrid_fixture_comparison.py` (4) runs both
providers over the committed PDF and its recorded Azure response, so a change to
either extractor that would flip a real document's routing fails in CI rather
than on a bill.

---

## Part 3 — Live-testing follow-up

Three real documents were tested: the French `required_optional_validation_test_form.pdf`
(committed as `fixtures/pdf/required-optional-validation-fr.pdf`), the Stuttgart
residence-permit form `32-41-1268-antrag-aufenthaltserlaubnis.pdf` (a real
government document, not committed), and the existing German rental contract.

### Encrypted-but-readable PDFs

The Stuttgart form was rejected at upload with "PDF is encrypted or
password-protected". It opens in every viewer without a prompt: like most
government forms it is encrypted for *permissions* with an empty user password.
`reader.is_encrypted` answers "does this file have an encryption dictionary?"
and says nothing about whether it can be read.

`app/documents/decryption.py::open_pdf` tries `decrypt("")` and reports
`pdf_password_required` only when that is refused. A second, hidden half: pypdf
reported a successful decrypt and then raised on first page access because
`cryptography` was not installed — a deployment problem surfacing as a document
problem. It is now pinned, and `open_pdf` probes the pages before returning.

Codes: `pdf_password_required`, `pdf_decryption_failed`, `pdf_invalid`.
Error messages no longer interpolate pypdf's own text, which can echo document
content.

### Coverage, not just quality

The quality score measures the candidates an extractor produced, and cannot see
what it missed. The French form produced **five** flawless candidates for a
two-page form of about thirty fields — score 0.83 against a 0.55 threshold, so
it was never escalated and the user saw five questions.

`app/field_detection/coverage.py` measures against the document instead: label
lines (trailing `*`, colon, "(Optional)") versus candidates; drawn selection
marks versus marks folded into option lists; pages that offered something
versus pages that produced something. Punctuation and geometry only — no
vocabulary, so it behaves identically in French, German and Arabic.

Escalation now requires quality **and** coverage, and the reason names the real
gap: `low_label_coverage`, `unclaimed_selection_marks`, `poor_page_coverage`.

Where the document offers no evidence, every ratio reports 1.0 — no evidence of
a gap is not evidence of a gap. That is what keeps the reference rental contract
free (3 pages, fields on 2, the third a signature block).

### Choice grouping generalized

Options were leaking as separate text questions. The cause was spacing, not
wording: segmentation is gap-based, and the professional-status row segments as

```
"(_) Salarie(e)" | "(_) Independant(e)" | "(_) Etudiant(e) (_) Demandeur d'emploi"
```

`_parse_option_row` required exactly one marker per segment, so the whole row
was rejected. A marker is an unambiguous boundary — everything from one marker
to the next is its label — which makes grouping independent of the spacing a
document happened to use.

### Declarations are not one question

Three declarations were folded into one `multiple_choice`, turning two mandatory
consents into "tick any of these" and offering a global Skip over the block.
`independent_boolean_options` splits any group whose *options* carry their own
requiredness markers into one boolean per option. The trigger is structural: a
choice question's requiredness belongs to the question, not to individual
answers, so an option carrying its own marker cannot be an option.

Requiredness markers are also stripped from display labels, which were reaching
the UI showing requiredness twice — and in the document's language inside an
interface in another one.

### Measured (local-only, committed fixtures)

| | candidates | quality | label cov | mark cov | routing |
|---|---|---|---|---|---|
| `required-optional-validation-fr.pdf` | 8 | 0.98 | 0.47 | 0.88 | escalate (`low_label_coverage`) |
| `rental-contract-de.pdf` | 19 | 0.83 | 1.00 | 1.00 | local |

All four reported grouping problems resolve on the French fixture: Genre and
Statut professionnel are single radio groups (the latter required), Langues
préférées is an optional multiple_choice, and the three declarations are
independent booleans with per-child requiredness.

### Carried

- Local text-field detection still finds only the choice groups on the French
  form; coverage-driven escalation is the safety net, not a substitute. The
  label-above-rule pass does not recognise that document's underline geometry.
- Three selection marks on the "Lieu et date" row remain unclaimed.
- Signature workflows (dedicated type, signature pad, sign-after-printing,
  export placement) are **not implemented**.
- Frontend rendering of `compound_boolean_group`, and suppression of the global
  Skip when a screen carries required children, are **not implemented** — the
  backend now models them correctly.
- Stuttgart-specific structures (yes/no rows, repeated children rows, table
  geometry) are not specifically handled; its unclaimed marks are what drives
  its escalation.
