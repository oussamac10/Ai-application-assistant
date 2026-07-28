# ADR 0012 — Automatic Confidence Routing and Upload-to-Questions Orchestration

**Status:** Accepted
**Phase:** 13 — Automatic Upload-to-Questions User Flow
**Date:** 2026-07-28

---

## Context

Phase 11 gave every uploaded, unknown PDF a technical field-review screen: a normal user had to
inspect detected candidate fields, correct labels/types, confirm each one, and only then trigger
question generation. That is appropriate for an admin/content reviewer, but it is not an
acceptable normal-user product experience — the product goal for Phase 13 is
`upload → analyze → detect fields → generate questions → start guided answering`, with the
technical review step preserved only for admin/development/debug use and genuine low-confidence
fallback cases.

This requires two things Phase 11 didn't have: a deterministic (non-AI) rule for deciding which
detected fields are safe to use without a human looking at them, and a single orchestration
entrypoint that composes analysis → OCR → detection → routing → question generation → session
creation into one idempotent call, instead of requiring the frontend to drive four separate
manual steps.

---

## Decisions

### 1. Confidence routing is plain configuration, not an AI decision

`app/field_detection/confidence.py` maps a candidate to `"confirmed"` / `"pending_review"` /
`"needs_clarification"` using only `FIELD_AUTO_CONFIRM_THRESHOLD` (default 0.75),
`FIELD_CLARIFICATION_THRESHOLD` (default 0.4), and two structural checks: the field's type must
be classifiable (not `"unknown"`), and a choice-shaped field (`radio`/`select`/`multiple_choice`)
must have at least one option. Ollama/AI plays no role in this decision — the same candidate
always routes the same way, which is what makes the policy testable
(`tests/field_detection/test_confidence.py`) and auditable. This directly follows the project's
"deterministic validation over AI" rule (`docs/claude/domain-rules.md`).

`"pending_review"` is deliberately reused rather than inventing a fourth status: in
`FIELD_DETECTION_REVIEW_MODE="auto"` it means "medium confidence, still usable automatically, but
flagged for later admin review" — not "awaiting human review" as it meant in Phase 11's manual
mode. A new terminal status, `"needs_clarification"`, was added to
`app/field_detection/constants.py::REVIEW_STATUSES` for the one case that must never silently
become a question.

### 2. `FIELD_DETECTION_REVIEW_MODE` toggles the assignment point, not the API surface

At detection time (`FieldDetectionService._candidate_to_model`), `"auto"` mode assigns
`review_status` immediately from the confidence router; `"manual"` mode preserves the exact Phase
11 behavior (every candidate starts `"pending_review"`, changed only by an explicit
PATCH/reject/confirm call). This means the Phase 11 review API, schemas, and frontend panel are
completely unmodified — only the value they start from differs by mode. The existing manual-mode
test suite (`tests/field_detection/test_field_detection_api.py`,
`tests/field_detection/test_question_bridge.py`) now pins `FIELD_DETECTION_REVIEW_MODE="manual"`
explicitly, since that suite documents the admin/debug contract, which is a distinct thing from
the new default.

### 3. One orchestration service, not a new state machine

`app/field_detection/orchestration.py::PrepareQuestionsService` composes
`SourceDocumentService`, `OCRService`, `FieldDetectionService`, and the question bridge exactly as
they already existed — it adds no new processing states of its own. It's synchronous, mirroring
every other document-processing call in this codebase (Phase 15's background-job phase is where
that would change, not this one). A single `POST /api/source-documents/{id}/prepare-questions`
call:

1. Reuses an existing non-terminal/completed session for the same document if one exists
   (idempotent — a retried request never creates a duplicate session).
2. Takes the known-template fast path with no OCR/detection/AI call at all, if the document
   matched a predefined template.
3. Otherwise runs OCR only if `next_step == "ocr_required"`, then field detection (both already
   idempotent — a "completed" result is reused, not recomputed).
4. Generates questions from every field the confidence router judged usable
   (`create_session_from_confirmed_fields(..., include_auto_usable=True)`), and creates the
   guided session.
5. Surfaces a plain-language uncertainty flag (count only, no field detail) when any field was
   routed to `"needs_clarification"`, without blocking the user from continuing.

A document that cannot be processed automatically (the existing `"review_required"` classification
from Phase 9, or a document detection that yields no usable questions) returns a safe status the
frontend maps to a plain message — the document and any partial results are preserved for retry,
matching the existing pattern of every other processing endpoint in this codebase.

### 4. Review metadata is persisted for Phase 14, without any private content

`FieldDetectionResult.review_metadata` (new nullable JSON column,
`897a1e1874ae_add_field_detection_review_metadata.py`) stores only counts —
`autoConfirmedCount`, `mediumConfidenceCount`, `needsClarificationCount`, `rejectedCount`,
`totalFieldCount` — computed by `question_bridge.build_review_metadata`. No field label, option
value, or answer ever enters this column, consistent with `docs/privacy.md`'s logging
restrictions. Phase 14 (administration and content review) can build a review queue from this
without Phase 13 needing to guess at what that queue's UI will look like.

### 5. Debug/admin access to the manual review screen is a build-time flag, not a role

Phase 14 owns real admin authentication; introducing a broad admin role now would be
speculative. `frontend/src/features/field-detection/debugMode.ts` gates the upload flow's link to
the unchanged `/application/document/{id}/detect-fields` screen behind
`NEXT_PUBLIC_ENABLE_DETECTION_DEBUG_UI=true`, or (outside a production build) a `?debug=1` query
param. The route itself is not additionally locked beyond its existing document-ownership check —
identical to how it was reachable in Phase 11 — so this is purely about what a normal user's UI
links to, not a new authorization boundary.

---

## Consequences

- Normal users never see confidence numbers, provider names, field keys, or bounding boxes —
  `PrepareQuestionsResponse` (`app/field_detection/schemas.py`) is deliberately shaped to exclude
  all of them.
- A medium-confidence field can end up in the guided flow without a human ever confirming it. This
  is an intentional product tradeoff (per Phase 13's spec: "do not block the normal user unless
  answer validation would be unsafe") — deterministic per-type answer validation
  (`docs/claude/domain-rules.md`) is the remaining safety net for those fields, exactly as it
  already is for every other answer in this system.
- The Phase 11 manual review test suite required an explicit mode pin
  (`FIELD_DETECTION_REVIEW_MODE="manual"`) to keep testing what it always tested; this is
  documented in the test files themselves so a future reader isn't confused why two suites set
  the same setting to opposite values.
