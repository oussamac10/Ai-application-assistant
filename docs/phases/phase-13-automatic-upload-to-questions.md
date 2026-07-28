# Phase 13 — Automatic Upload-to-Questions User Flow

**Branch:** `feature/automatic-upload-to-questions`
**Base:** `feature/user-accounts-persistent-sessions`
**Status:** Complete

## Objective

Replace the normal-user unknown-form workflow — upload → detect fields → manually review every
detected field → confirm fields → generate questions → answer — with: upload → analyze → detect
fields → automatically decide what is usable → generate questions → begin guided answering.
Normal users are never required to review technical field definitions. The full ADR is
[0012](../decisions/0012-automatic-confidence-routing.md).

## What changed

### Backend

- `app/core/config.py`: `FIELD_AUTO_CONFIRM_THRESHOLD` (0.75), `FIELD_CLARIFICATION_THRESHOLD`
  (0.4), `FIELD_DETECTION_REVIEW_MODE` (`auto` default / `manual`).
- `app/field_detection/confidence.py` (new): deterministic routing —
  `decide_auto_review_status(candidate) -> "confirmed" | "pending_review" | "needs_clarification"`.
- `app/field_detection/constants.py`: added `"needs_clarification"` to `REVIEW_STATUSES`.
- `app/field_detection/service.py`: `_candidate_to_model` assigns `review_status` from the router
  in `auto` mode; unchanged (`pending_review`) in `manual` mode.
- `app/field_detection/question_bridge.py`: `create_session_from_confirmed_fields` gained
  `include_auto_usable: bool = False` (default preserves the exact Phase 11 "only explicitly
  confirmed fields" contract) and `build_review_metadata()`.
- `app/field_detection/orchestration.py` (new): `PrepareQuestionsService.prepare()` — the single
  idempotent orchestration entrypoint.
- `app/field_detection/schemas.py`: `PrepareQuestionsResponse` / `UncertaintyInfoSchema` — a
  plain-language-safe response shape with no confidence/provider/field-key detail.
- `app/field_detection/api/routes.py`: `POST /api/source-documents/{id}/prepare-questions`.
- `app/field_detection/models.py` + migration `897a1e1874ae`: `FieldDetectionResult.review_metadata`
  (nullable JSON) — safe counts only, for Phase 14.
- `app/sessions/repositories.py`: `get_latest_session_by_source_document_id` — idempotency lookup.

### Frontend

- `features/document-upload/components/DocumentUploadForm.tsx`: after upload+analysis, calls
  `prepareQuestions` automatically instead of showing per-`nextStep` manual action buttons.
  New stages: `processing` (plain progress message), `uncertain` (plain-language banner + a single
  "Continue" action), `review_required` (safe failure message + retry). The old `success` panel
  with structural analysis detail and "Detect Fields"/"Start OCR"/"Start Guided Form" buttons is
  gone from the default path.
- `features/field-detection/services/apiClient.ts`: `prepareQuestions()`.
- `features/field-detection/types/index.ts`: `PrepareQuestionsResponseSchema`.
- `features/field-detection/debugMode.ts` (new): `isDetectionDebugUiEnabled()` — gates a link to
  the unchanged Phase 11 `/application/document/{id}/detect-fields` screen.
- `messages/{en,de,fr,ar}.json`: new `documentUpload.*` keys for the plain-language progress/
  uncertainty/failure messages.

### What did not change

- The Phase 11 field-detection review API and screen (`detect-fields` page,
  `FieldDetectionPanel`) — fully intact, reachable directly, and covered by its own (mode-pinned)
  test suite.
- Known-template fast path (`SourceDocumentService.create_session_from_document`) — untouched;
  `PrepareQuestionsService` calls it as-is with no OCR/detection/AI.
- Dynamic unknown-PDF PDF export remains unsupported (deferred to Phase 15) — orchestration never
  touches the export endpoints.
- Dual ownership (Phase 12) — `PrepareQuestionsService` takes the same `current_user_id` +
  ownership-token pair every other document/session endpoint takes and delegates all authorization
  checks to the existing services unchanged.

## Confidence routing

| Confidence | Condition | Outcome |
|---|---|---|
| High (`>= FIELD_AUTO_CONFIRM_THRESHOLD`) | classifiable type; choice types have options | `confirmed` — auto-confirmed, question generated, no review flag |
| Medium (`>= FIELD_CLARIFICATION_THRESHOLD`) | same structural requirements | `pending_review` — question still generated automatically, flagged for later admin review |
| Low (`< FIELD_CLARIFICATION_THRESHOLD`), unclassifiable type, or choice field missing options | — | `needs_clarification` — never used to generate a question; counted in the uncertainty flag |

Thresholds are plain configuration; the decision (`app/field_detection/confidence.py`) takes no
AI input and is fully unit-tested (`tests/field_detection/test_confidence.py`).

## Uncertainty handling (normal user)

When at least one field routes to `needs_clarification` but at least one usable field remains, the
session is still created and the response carries `uncertainty: { hasUncertainFields,
uncertainFieldCount }` — the frontend shows a plain banner ("One section may need confirmation")
with a single "Continue" action. When *no* field is usable, the response returns
`status: "needs_clarification"` with no session, and the frontend shows a safe "we could not
process this document" message with a retry option — the document and any partial results are
preserved.

## Idempotency

- A repeated `prepare-questions` call for the same document reuses an existing non-terminal or
  completed session rather than creating a duplicate one (`reusedExistingSession: true`,
  no fresh `ownershipToken` — the caller already has one from the first successful call, or
  authenticates via the auth cookie).
- OCR and field detection are each independently idempotent already (Phase 10/11): a `"completed"`
  result is returned as-is, never recomputed.
- Resuming a guided session (reloading `/application/session/{id}`) never re-triggers upload
  processing — the session page only ever calls session/answer endpoints.

## Known limitations

- OCR language for the automatic flow defaults to the user's interface language (falling back to
  `en` if unsupported by Tesseract) since the pipeline has no document-language detection step —
  same limitation the Phase 10 manual OCR flow already had.
- `PrepareQuestionsService` is synchronous, matching every other processing endpoint in this
  codebase; a large/slow document blocks the request for its full processing time. Phase 17
  (background jobs) is the intended place to change this.
- The debug/admin review route is reachable by anyone who knows the document's URL and ownership
  token — identical to its Phase 11 exposure. Phase 14 is where real admin authentication is
  introduced.
- `review_metadata`'s `questionGenerationFallbackUsed` field described in the original phase
  request was not implemented — tracking whether an individual field's AI translation fell back to
  source text would require threading a per-field flag through `translate_text`, which was judged
  out of scope for this phase's synchronous orchestration; the existing fallback behavior (safe
  source-text use on AI failure) itself is unchanged and still applies.

## Manual verification performed

1. Known template (`basic-registration-v1.pdf`) → guided session starts immediately, no OCR/
   detection/manual-review UI. (Playwright, Docker `local`/`ollama` providers.)
2. Unknown digital PDF with a clear text field → guided session starts automatically with the
   correct question label, no manual review screen. (Playwright.)
3. Scanned PDF → OCR runs automatically, no "Start OCR" button shown. (Playwright.)
4. Resuming an already-processed session does not reprocess or duplicate the session. (Playwright.)
5. Arabic (`dir="rtl"`) stays active through the automatic processing screen. (Playwright.)
6. Backend: 334 tests pass (312 baseline + 22 new); ruff/mypy clean; migration round-trips.
7. Frontend: 81 tests pass (77 baseline + 4 new); lint/typecheck clean.
