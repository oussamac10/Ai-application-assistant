# Privacy Policy & Privacy by Design

The AI Form Assistant is built on the core principle of **Privacy by Design**. This document outlines how temporary form sessions respect and enforce user privacy.

## 1. Data Minimization
At the session level, we collect and store only the minimal technical metadata required to guide the user through the form-filling workflow:
- `user_language`: The language selected for questions and instructions.
- `output_language`: The language the completed form is exported in.
- `status`: The workflow stage (`session_created`, `in_progress`, etc.).
- Progress indicators (`current_field_position` and `total_required_fields`).

**No personal data, email addresses, names, or form responses are associated with or stored in the session record itself in this phase.**

## 2. Temporary Anonymous Sessions
- Sessions are entirely anonymous. We do not require or create permanent user accounts.
- Access to sessions is authenticated solely via high-entropy, cryptographically secure ownership tokens.
- We do not expose internal primary keys in URLs or API calls, utilizing a randomized, opaque UUID `public_id` for external references.

## 3. Ephemeral Storage (Expiration Rules)
- All sessions are temporary and live for a configurable duration (default: `24 hours`), controlled by the `FORM_SESSION_TTL_HOURS` backend configuration.
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

## 5. Ephemeral Answers Storage
- Form answers are stored in the database only for the duration of the active session.
- When a session is deleted, all corresponding `form_answers` rows are deleted automatically via database cascade deletes.
- Answers are only available to the client who provides the correct `X-Session-Token` header.

