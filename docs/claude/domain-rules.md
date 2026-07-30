# Domain Rules

Durable product/domain rules extracted from `.agents/AGENTS.md` that are not already
covered in `working-rules.md`, `commands.md`, or `project-overview.md`. Read this
instead of the full `AGENTS.md` for day-to-day phase work; consult `AGENTS.md` directly
only for a rule not covered here.

## Language model

Three distinct language concepts — never conflate them:

- `sourceLanguage`: language of the original form
- `userLanguage`: language used for questions and explanations
- `outputLanguage`: language used in the completed form

Never hardcode a default output language in business logic. `sourceLanguage` and
`outputLanguage` are often equal but must remain separate properties.

## Core product principles

- **Never invent information.** Missing or ambiguous input requires a clarification
  question, not a guessed value.
- **Preserve original answers.** Always store the user's original answer alongside any
  normalized/translated value.
- **Require confirmation.** Extracted, translated, normalized, or transliterated values
  must be confirmed by the user before being treated as final.
- **Prefer canonical values.** Use ISO 639 (language), ISO 3166 (country), ISO 4217
  (currency), ISO 8601 (date) wherever possible.
- **Deterministic validation over AI.** Use plain code for required fields, emails,
  dates, phone numbers, numeric ranges, country/currency codes, yes/no, predefined
  choices, file/MIME validation, IBAN checks. Use AI only when language understanding
  is genuinely required.
- **Never transliterate a name automatically** without explicit user confirmation.

## Product boundaries

The assistant is not a lawyer, government authority, financial/immigration/medical
adviser, identity-verification system, or an eligibility/approval decision system. It
must never invent missing personal data, make legal conclusions, determine eligibility,
silently change confirmed values, or submit forms without explicit user action.

## Hybrid reusable question resolution

Questions are identified by stable semantic keys (e.g. `personal.first_name`), not by
displayed text. Resolution order:

```text
1. approved reusable question in userLanguage
2. approved reusable question in sourceLanguage
3. approved static translation from the immutable form version
4. AI translation of an approved source-language question
5. AI generation from minimal field metadata
6. deterministic non-AI fallback
```

Do not call AI when an approved reusable question or static translation already exists.
AI-generated/translated questions default to `reviewStatus: pending_review` and must
never silently overwrite an approved manual or static translation. A deterministic
fallback must always be available when AI is unavailable.

AI requests for question resolution must contain only the semantic key, field type,
minimal config, approved source text (if any), and the three language codes — never the
full form, prior answers, tokens, or secrets.

## Provider abstractions

Business logic must depend on an interface, not a concrete vendor, for anything
pluggable: `AIProvider`, `OCRProvider`, `StorageProvider`, `TranslationProvider`,
`PDFRenderer`. Only implement the provider(s) the current phase actually needs. Every
provider family needs a deterministic mock/fixture-based implementation for tests —
automated tests must never call a live/paid provider.

## Requiredness

A field records what the *document* declared, in three states — `required`, `optional`,
`unknown` — never a boolean. `unknown` is the ordinary case for a detected form and must
never be collapsed into either direction: resolving it to `required` blocks a user on a
question the form never asked, and resolving it to `optional` claims the document said
something it did not. The UI shows a requiredness label only for a real finding.

Requiredness comes from evidence only (native flag, adjacent asterisk, explicit marker
word in any supported language, trusted metadata, or a form-level "all fields are
required" statement). A field's apparent importance is never evidence — a surname with no
marker stays `unknown`.

Skipping is allowed for `optional` **and** `unknown`, refused for `required`. A skip is its
own state with null values, never an empty string.

## Answer and session state

Answers use independent status dimensions, not one combined field:

- `status`: `unanswered | draft | needs_clarification | awaiting_confirmation | confirmed`
- `validationStatus`: `not_checked | valid | invalid`
- `translationStatus`: `not_required | pending | completed | failed`

Never ask an LLM to invent a numeric confidence score — a confidence value may only be
stored when it comes from a provider with documented confidence semantics (e.g. an OCR
engine).

Session-level state machine: `session_created → in_progress → awaiting_final_confirmation
→ ready_for_export → completed`, with terminal/exceptional states `expired | cancelled |
deleted | failed`. Individual answer-processing states belong to answers, not the
session.

Beyond `status`, an answer has a derived **answer state**: `unreached | unanswered |
skipped | answered | invalid` — what the *user* did, as opposed to what the document
demanded. The two are independent and neither is inferred from the other; only their
cross-product decides what blocks confirmation. Absence blocks only where the document
demanded an answer; an invalid *value* blocks regardless of requiredness.

Value validators, normalization, clarification and the AI provider only ever receive an
actual submitted value. A blank submission is refused rather than stored — it is neither
an answer nor a skip, and storing it makes validators report on a value that does not
exist.

## PDF export

No coordinate guessing. Each field mapping must define: field ID, page number, AcroForm
field name or coordinates, font size, max length, overflow behavior, alignment,
formatting rule. Export requires all required fields complete, no unresolved
invalid/clarification states, and explicit user confirmation. Export creation must be
idempotent.

## Dependency rules

Before adding a dependency, check: active maintenance, compatible license, no existing
duplicate capability, acceptable security history, supported runtime/deployment
platform, reasonable size/operational cost. Pin direct dependencies; commit lock files;
document why a new dependency is needed.

## Definition of done

A task is complete only when: acceptance criteria are met, relevant tests exist and
pass, formatting/linting/type-checks pass, migrations are included where needed, docs
are updated, error handling and security implications are considered, multilingual
behavior is tested where relevant, no sensitive data is committed, no paid AI API was
called by automated tests, and unrelated functionality was left untouched.

## Full reference

For anything not covered above (detailed form-model JSON shapes, prompt-file
versioning conventions, initial per-phase task breakdowns 1–7), see
`.agents/AGENTS.md` directly.
