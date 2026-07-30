# Privacy Policy & Privacy by Design

The AI Form Assistant is built on the core principle of **Privacy by Design**. This document outlines how temporary form sessions respect and enforce user privacy.

## 1. Data Minimization
At the session level, we collect and store only the minimal technical metadata required to guide the user through the form-filling workflow:
- `user_language`: The language selected for questions and instructions.
- `output_language`: The language the completed form is exported in.
- `status`: The workflow stage (`session_created`, `in_progress`, etc.).
- Progress indicators (`current_field_position` and `total_required_fields`).

**No personal data, email addresses, names, or form responses are associated with or stored in the session record itself in this phase.**

## 2. Temporary Anonymous Sessions (and Optional Accounts)
- Sessions remain anonymous by default. Creating an account is entirely optional (Phase 12) and only stores an email address and a salted password hash — never a plaintext password.
- Anonymous access to sessions is authenticated solely via high-entropy, cryptographically secure ownership tokens.
- A user may explicitly choose to "claim" (save) an anonymous session into their account. From that point the session is retained under account ownership rather than expiring anonymously, and the original anonymous token is permanently invalidated — see [`docs/user-accounts.md`](user-accounts.md).
- We do not expose internal primary keys in URLs or API calls, utilizing a randomized, opaque UUID `public_id` for external references.

## 3. Ephemeral Storage (Expiration Rules)
- Anonymous sessions are temporary and live for a configurable duration (default: `24 hours`), controlled by the `FORM_SESSION_TTL_HOURS` backend configuration. A session claimed into an account is no longer time-boxed by this anonymous TTL — it persists until the account holder deletes it (soft-deleted, not recoverable).
- Once a session crosses its expiration threshold, it is considered dead:
  - Accessing it via the API immediately transition-triggers its status to `expired`.
  - It becomes immutable; no further state transitions or operations can be performed.
- A background cleanup CLI utility (`python -m app.commands.cleanup_expired_sessions`) finds and updates expired sessions.

## 4. Logging & Audit Restrictions
To prevent accidental data exposure:
- Raw session ownership tokens and token hashes are **never logged**.
- We never log the session's internal database ID or full request headers in application logs.
- Form answers (`original_answer`, `normalized_value`, `output_value`) are strictly excluded from all application logs, tracebacks, and stdout/stderr messages.
- Log statements report only high-level actions, public identifiers (`public_id`), and execution metrics.

## 5. Automatic Upload-to-Questions Review Metadata (Phase 13)

`FieldDetectionResult.review_metadata` stores only aggregate counts (auto-confirmed / medium-
confidence / needs-clarification / rejected / total field counts) for later Phase 14 admin review
— never a field label, detected value, option text, or user answer. The normal-user response from
`POST /api/source-documents/{id}/prepare-questions` carries only a session id, an ownership token,
and a count of uncertain fields — no document content.

## 5b. Third-Party Document Processing (Phase 14, opt-in)

By default every stage of processing runs on this system: the local field detector and the
local OCR provider never send a document anywhere.

Selecting the optional Azure provider (`FIELD_DETECTION_PROVIDER=azure`) changes that
materially: **the uploaded PDF is transmitted to Microsoft Azure Document Intelligence for
analysis.** Because that is a genuine change in who can see a user's document, it is
disabled by default and requires two explicit settings
(`AZURE_DOCUMENT_INTELLIGENCE_ENABLED=true` *and* `FIELD_DETECTION_PROVIDER=azure`).
Operators enabling it are responsible for reflecting that transfer in their own privacy
notice and for choosing an appropriate Azure region.

`provider_usage_records` stores metadata *about* each provider request — provider, model
id, page count, duration, success/failure, error code, Azure's request id, and whether the
result was served from cache. It never stores document text, extracted field labels or
values, answers, or credentials.

## 5c. Third-Party Translation (Phase 15, opt-in)

Selecting `TRANSLATION_PROVIDER=azure` sends **field labels and choice-option labels** to Microsoft
Azure Translator. It does not send the document, its full text, or any answer a user typed — only
the short label strings that must be displayed in the user's language.

What is deliberately withheld even from that:

- Text that is entirely an identifier — email addresses, IBANs, BICs, dates, phone numbers,
  currency amounts, URLs, UUIDs, internal keys — is detected deterministically
  (`app/translation/protected.py`) and never transmitted.
- Stable choice **values** are never translated, in any provider path.
- Anything already resolved from the approved question catalog, a persisted translation, or the
  in-process cache is never transmitted, because it is never requested.

Like the Phase 14 document provider, this is off by default and needs two explicit settings
(`AZURE_TRANSLATOR_ENABLED=true` *and* `TRANSLATION_PROVIDER=azure`). The default
`TRANSLATION_PROVIDER=ollama` keeps every translation on this system.

Only the interface language is translated during question preparation; the output language is
translated later, and only if review or export actually needs it — so a user who never reaches
review never has that text sent anywhere.

Translation logs record counts, durations and language codes only: no label, option value,
translated string, API key or provider response body is written to a log.

## 6. Ephemeral Answers Storage
- Form answers are stored in the database only for the duration of the active session.
- When a session is deleted, all corresponding `form_answers` rows are deleted automatically via database cascade deletes.
- Answers are only available to the client who provides the correct `X-Session-Token` header.

