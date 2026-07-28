# Current Phase

## Phase

Phase 13 - Automatic Upload-to-Questions User Flow

## Branch

`feature/automatic-upload-to-questions`

## Base

`feature/user-accounts-persistent-sessions`

## Objective

Replace the normal-user unknown-form workflow (upload → detect fields → manually review every
detected field → confirm fields → generate questions → answer) with an automatic flow: upload →
analyze → detect fields → automatically decide what is usable → generate questions → begin guided
answering. Normal users must not be required to review technical field definitions. The Phase 11
field-review UI remains available only for admin/development/debug use and genuine low-confidence
fallback cases.

## Reuse

- `FieldDetectionResult`/`DetectedField` (Phase 11) — confidence routing is layered on top, not a
  replacement
- `create_session_from_confirmed_fields` (Phase 11 question bridge) — extended to optionally
  include auto-usable (not just manually confirmed) fields
- dual-ownership authorization (Phase 12) — reused unmodified for the new orchestration endpoint
- existing OCR/field-detection idempotent request/reuse pattern — orchestration composes these
  services rather than re-implementing detection or OCR

## In scope

- deterministic confidence routing (`FIELD_AUTO_CONFIRM_THRESHOLD`,
  `FIELD_CLARIFICATION_THRESHOLD`, `FIELD_DETECTION_REVIEW_MODE`)
- single idempotent orchestration endpoint:
  `POST /api/source-documents/{id}/prepare-questions`
- automatic question generation from high/medium-confidence fields; low-confidence fields excluded
  and surfaced only as a plain-language uncertainty flag
- review metadata persisted on `FieldDetectionResult` for later Phase 14 consumption
- frontend: upload goes straight to guided questions with simple progress messages; no mandatory
  field-review step; existing Phase 11 review UI preserved behind a development-only debug flag
- known predefined forms keep their existing fast path (no OCR/detection/AI)
- backend/frontend tests for the new orchestration and confidence-routing behavior

## Out of scope

- Phase 14 (administration and content review) — only review metadata is persisted, no admin UI/role
- Phase 15 (dynamic PDF mapping, filling, preview, export of arbitrary unknown PDFs)
- background job queues — orchestration remains synchronous, matching the existing OCR/detection
  request pattern
- changes to the PDF structural analyzer's `next_step` classification itself (Phase 9)

## Status

In progress.

See `docs/phases/phase-13-automatic-upload-to-questions.md` for the full specification (once
written) and `docs/decisions/0012-automatic-confidence-routing.md` for the architecture decision.
