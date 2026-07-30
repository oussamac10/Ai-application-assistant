# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Phase 15 follow-up: automatic document-language detection, honest provider metrics, RTL field
grouping, and removal of the output-language selector. Azure Translator is now live and verified.

### What was actually wrong

Live testing produced this log line:

```
provider=azure  provider_latency=42.62s  detected_source=en  fallback_calls=1
```

Every part of it was misleading, and it took four separate fixes:

1. **No document-language detection existed.** `detected_source=en` was Ollama's *assumed*
   language recorded as if it were a detection. Azure's `detectedLanguage` could never have
   filled the gap on its own — it only arrives *with* a translation, so a document needing none
   has no answer.
2. **One combined latency field.** Azure was failing in ~0.15 s; Ollama was spending the 42.6 s.
3. **Counters incremented on provider *selection*.** That produced the impossible
   `provider_calls=1 characters=0 latency=0.00s`.
4. **`normalize_field_name` stripped non-ASCII**, so every Arabic label became the literal
   `"field"` and deduplication collapsed a 27-field form into 2 questions. Separately, Azure
   merged three rows into one key-value pair.

### What was built

- `app/language/` — `DocumentLanguageDetector` (local, deterministic, dependency-free; script
  first, then function-word frequency), filtered sampling, persistence on `source_documents`
  (migration `e1975a7403eb`), reuse, documented precedence, and `und` as a real answer.
- `TranslationUsage.source_language_is_detected` — an assumption can no longer outvote a real
  detection.
- Separate `primary_*` / `fallback_*` metrics plus `fallback_reason`; counters come from real
  outbound requests; a failed call carries its own cost on the exception.
- Azure custom-subdomain path (`/translator/text/v3.0/translate`) *and* the global `/translate`,
  with 404 mapped to `endpoint_not_found` and never retried.
- `normalize_field_name`: ASCII slug first (German/English byte-identical), Unicode fallback,
  deterministic hash for punctuation-only labels.
- Multi-line Azure key-value keys split into one candidate per line.
- Direction-aware geometry for `ar`/`he`/`fa`/`ur`.
- `tests/conftest.py` pins providers so the suite never calls a live service.
- The upload flow's "Select completed form language" dropdown is gone; `outputLanguage` is
  optional and resolved from the detected document language.

## Third round — question shape (options, compound fields, requiredness)

Live French-form testing showed the pipeline preserving a document's *text* but losing its
*semantics*. Fixed:

- `app/field_detection/option_groups.py` — a selection-mark row becomes **one** question.
  Previously each option became its own free-text question and the real question never
  existed. Group naming: recognised option set -> section heading -> neutral + review flag.
  One question per row, never merged (adjacent rows can be unrelated questions).
- `classification.compound_concepts()` — "Code postal, ville" keeps `address` (which is
  permissive) while unrelated pairs ("Lieu et date") fall back to `text`. The rejection of
  `70188, Stuttgart` was the address validator demanding street *and* city; it now needs
  one recognisable part.
- `app/field_detection/requiredness.py` — three states from evidence. Everything defaulted
  to required before, blocking users on fields the form never insisted on. No evidence ->
  `unknown`, which never blocks.
- `app/answers/normalization/context.py` — proper-noun labels pin the answer's **output**
  value verbatim (`stuttgart` was being transliterated into Arabic); currency comes from
  the label (`2000` was becoming `USD 2000`), with an invented currency removed but a
  user-typed one kept.
- Validation errors render once: field-level for 400/422, banner for global failures.
- French language detection fixed by weighting function words by how many languages claim
  them ("de" says little, "vous" is decisive) and keeping only discriminative diacritics.

Result (French form, Arabic UI): 6 option groups, 23 options folded in, **0** option labels
leaking as text questions, `Code postal, ville` accepting `70188, Stuttgart`, 38 fields
`unknown` requiredness and none blocking, 4.64 s. German and Arabic unchanged.

**Two regressions this introduced, found and fixed:** progress read "Question 1 of 0
(100%)" and the summary was unreachable, both because they counted *required* fields only.
`ProgressInfo` gained `totalQuestions`/`answeredQuestions`.

## Live results (Azure Translator working, global endpoint)

| | German (UI fr) | Arabic (UI en) | German (UI ar) |
|---|---|---|---|
| `source_language` | **de** (0.89) | **ar** (0.99) | de |
| Azure primary | 1 req, 0.15 s, `2xx` | 1 req, 0.21 s, `2xx` | 1 req, 0.35 s, `2xx` |
| Fallback | 0 | 0 | 0 |
| Translation total | **0.19 s** | **0.45 s** | 0.40 s |
| Total | **5.36 s** | **5.92 s** | 5.35 s |
| Questions | 24 | **29** (was 2) | 24 |

Repeat request: 0.046 s, zero provider calls. Merged multi-label questions: 0. Stable choice
values unchanged. Arabic byte-intact.

## Verification

Backend **666 passed**, ruff clean, `ruff format --check` clean, mypy clean (151 files),
migration `e1975a7403eb` round-trips. Frontend **133 passed**, lint and typecheck clean.
Playwright: see `TODO.md` — several specs were retrofitted because they drove the removed
`#upload-output-select`.

## Operational gotchas worth remembering

- `docker compose restart` does **not** re-read `.env`; use `up -d --force-recreate`. A stale
  container showed the old endpoint and key while the file on disk was already correct.
- Never run backend pytest and Playwright against the same dev database at once — pytest
  `TRUNCATE`s `form_templates` and wipes the fixture mid-run.

## Known limitations carried forward

- The local detector covers Latin-script European languages and the major non-Latin scripts; it
  is not a general-purpose language identifier.
- Azure's key-value grouping remains the dominant signal for Arabic forms — the local text
  passes contribute only one candidate there.
- The translation cache is process-local and dropped on restart.
- Preparation is still synchronous; background jobs remain Phase 20.
- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9).
- Azure Document Intelligence F0 rate-limits the E2E suite (`HTTP 429`); affected specs
  pass when re-run after a pause.
- A long wrapped checklist splits into one question per row (never merged).
- Azure mistranslates some isolated one-word options (`Français` -> `الإنجليزية`), verified
  as provider quality with correct per-item ids, not an id-mapping fault.

## Next action

Phase 15 is complete and verified end to end. Do not start Phase 16 until explicitly requested.

## Decisions

[ADR 0015](../decisions/0015-translation-provider-and-azure-translator.md), including the
addendum covering detection, metrics and RTL grouping.
