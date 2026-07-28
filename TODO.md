# Project TODO

## Completed Phases

| Phase | Branch | Status |
|---|---|---|
| 1 — Project Foundation | `main` | ✅ Done |
| 2 — Form Definitions and Versioning | `feature/form-definitions-versioning` | ✅ Done |
| 3 — Temporary Anonymous Sessions | `feature/anonymous-sessions` | ✅ Done |
| 4 — Mock Question and Answer Workflow | `feature/mock-qa-workflow` | ✅ Done |
| 5 — Local AI Integration with Ollama | `feature/local-ai-ollama` | ✅ Done |
| 6 — Reusable Question Catalog and Hybrid Resolution | `feature/question-catalog-hybrid-resolution` | ✅ Done |
| 7 — Frontend Guided Form Experience | `feature/frontend-guided-experience` | ✅ Done |
| 8 — PDF Template Mapping and Export | `feature/pdf-template-export` | ✅ Done |
| 9 — Form Upload and Document Analysis | `feature/form-upload-analysis` | ✅ Done |
| 10 — OCR Integration | `feature/ocr-integration` | ✅ Done |
| 11 — Dynamic Field Detection | `feature/dynamic-field-detection` | ✅ Done |
| 12 — User Accounts and Persistent Sessions | `feature/user-accounts-persistent-sessions` | ✅ Done |

Archived phase TODOs live under `docs/progress/`.

---

## Current Task

**Phase 13 — Automatic Upload-to-Questions User Flow.** Branch: `feature/automatic-upload-to-questions`. Base: `feature/user-accounts-persistent-sessions`. **Status: Complete.**

## Goal

Replace the normal-user unknown-form workflow (upload → detect fields → manually review every
detected field → confirm fields → generate questions → answer) with: upload → analyze → detect
fields → automatically decide what is usable → generate questions → begin guided answering.
Normal users must never be required to review raw field detection output. See
`docs/claude/current-phase.md` for the full scope.

## Acceptance Criteria

- [x] Deterministic confidence-routing config (`FIELD_AUTO_CONFIRM_THRESHOLD`,
      `FIELD_CLARIFICATION_THRESHOLD`, `FIELD_DETECTION_REVIEW_MODE`) — no AI-decided routing
- [x] Auto-confirm rules implemented per field type; unclassifiable (`unknown`) type never
      auto-confirmed; choice fields without options never auto-confirmed
- [x] Duplicate/overlap handling preserved (Phase 11's `normalization.py` dedup/ordering, reused
      unmodified — no changes needed for this phase)
- [x] Single idempotent orchestration endpoint composing analyze → OCR (if needed) → detect →
      auto-confirm → generate questions → create/reuse session
- [x] Known predefined forms bypass OCR/detection/AI entirely (fast path preserved)
- [x] Existing completed detection/OCR/question results are reused, never redundantly recomputed
- [x] Question generation resolution order preserved unmodified (question_bridge/resolver untouched)
- [x] Choice field configuration (stable `value`, ordered `displayLabel` options) preserved
      end-to-end (unchanged path, only which fields are included changed)
- [x] Review metadata persisted on `FieldDetectionResult` for later Phase 14 consumption, without
      exposing private answers
- [x] Normal-user uncertainty handling: uncertain fields excluded from question generation, never
      silently guessed into an unsafe question
- [x] Frontend: upload → automatic processing → guided questions, with plain-language progress
      messages only; no raw field-review UI shown by default
- [x] Phase 11 field-review UI preserved behind an explicit development/debug-only gate
- [x] Dual ownership (Phase 12) preserved for every new/changed endpoint; no IDOR
- [x] Resume does not reprocess (no duplicate OCR/detection/session/AI calls)
- [x] Backend/frontend/Playwright tests for the new behavior
- [x] ADR 0012; `docs/phases/phase-13-automatic-upload-to-questions.md`; updated
      `docs/architecture.md`, `docs/security.md`, `docs/privacy.md`, `docs/field-detection.md`,
      `docs/user-accounts.md`, `.env.example`, `docker-compose.yml`

## Planned Steps

- [x] Phase initialization and documentation (this file, current-phase.md, roadmap, archive Phase 12)
- [x] Confidence-routing config + deterministic decision module + tests
- [x] Auto-assign `DetectedField.review_status` at detection time in `auto` mode; preserve legacy
      `manual` mode for the existing Phase 11 review UI
- [x] Extend question-bridge session creation to optionally include auto-usable (not just manually
      confirmed) fields; add review-metadata persistence + migration
- [x] Orchestration service + `POST /api/source-documents/{id}/prepare-questions` endpoint
- [x] Frontend: automatic upload → processing → guided-session flow; simple progress messages;
      uncertainty screen; debug-mode gate for the Phase 11 review UI
- [x] Backend/frontend/Playwright tests
- [x] Documentation, `.env.example`, verification pass

## Decisions and Assumptions

- `"pending_review"` is reused (not replaced) as the "medium confidence, auto-usable" status in
  `auto` mode, rather than inventing a fourth status — see ADR 0012 §1.
- `FIELD_DETECTION_REVIEW_MODE` controls only *when* `review_status` is assigned, not the API
  surface — the Phase 11 manual review endpoints/schemas/UI are completely unchanged (ADR 0012 §2).
- `PrepareQuestionsService` stays synchronous, matching every existing OCR/detection endpoint;
  background processing is explicitly deferred to Phase 17.
- OCR language for the automatic flow defaults to the user's interface language (falls back to
  `en` if unsupported) — no document-language detection exists yet; same limitation Phase 10 had.
- `questionGenerationFallbackUsed` (listed as example review-metadata in the original request) was
  not implemented — would require threading a per-field AI-fallback flag through `translate_text`;
  judged out of scope for this phase. The underlying safe-fallback behavior is unaffected.
- The debug/admin review route is gated only by a build-time flag / dev-only query param, not a
  new auth role — a broad admin role was explicitly out of scope per the phase brief; Phase 14
  owns real admin authentication.

## Blockers

None encountered.

## Verification

Ran directly via `backend/venv/bin/python` (not Docker) for pytest/ruff/mypy/alembic, and against
the rebuilt Docker stack (`docker compose build backend frontend && docker compose up -d`) for
Playwright, per this session's instructions.

- `venv/bin/python -m pytest -q` (`PYTHONPATH=.`) → **334 passed**, 0 failed, 0 skipped (312
  baseline + 22 new: 10 in `test_confidence.py`, 9 in `test_orchestration.py`, 3 in
  `test_prepare_questions_api.py`).
- `venv/bin/python -m ruff check .` → All checks passed.
- `venv/bin/python -m ruff format --check .` on changed files → clean (all Phase 13 files
  formatted); the one pre-existing `tests/documents/test_documents.py`/`app/documents/*.py`
  formatting exception (documented since Phase 10) is untouched, as instructed.
- `venv/bin/python -m mypy app` → Success: no issues found in 130 source files.
- `venv/bin/python -m alembic downgrade -1` then `upgrade head` → clean round-trip for
  `897a1e1874ae_add_field_detection_review_metadata.py`.
- `cd frontend && npm run typecheck` → clean.
- `npm run lint` → "No ESLint warnings or errors".
- `npm test` → **81 passed** (0 failed): 77 baseline + 4 new
  (`document-upload-automatic-flow.test.tsx`).
- `CI=true PLAYWRIGHT_BASE_URL=http://localhost:3003 npx playwright test` (rebuilt Docker images,
  `FIELD_DETECTION_PROVIDER=local`, `OCR_PROVIDER=local`, `AI_PROVIDER=ollama`) → **27 passed**,
  **1 failed** (`guided-flow.spec.ts` — the pre-existing default-tab gap, documented since Phase
  9/10, unrelated to this phase), 0 skipped. One test
  (`dynamic-field-detection-flow.spec.ts`'s unknown-digital-PDF auto flow) was flaky on first
  attempt (timing, passed on retry) — see "Known limitations" in the phase doc.
- Retrofitted 5 existing Phase 9/10/11 Playwright specs
  (`dynamic-field-detection-flow.spec.ts`, `ocr-flow.spec.ts`, `upload-analysis-flow.spec.ts`,
  `select-manually-translation-flow.spec.ts`) whose assertions depended on the now-removed manual
  "Detect Fields"/"Start OCR"/"Document Analysis Complete" UI; added
  `automatic-upload-to-questions-flow.spec.ts` for resume idempotency.
- Fixed a real bug found by the new orchestration tests: `PrepareQuestionsService._run_ocr` was
  passing `None` instead of the caller's ownership token to `OCRService.request_ocr`, which would
  have broken the scanned-PDF automatic flow for every anonymous (non-authenticated) user.
- Fixed a real regression introduced during the frontend refactor: the top-level error banner's
  render condition was narrowed to `stage === "error"`, which hid client-side file-validation
  errors (invalid type / too large) since those never change `stage` away from `"idle"`.

---

## Next Phases (not yet started)

| Phase | Description |
|---|---|
| **14** | Administration and content review |
| **15** | Dynamic PDF mapping, filling, preview, and export |

---

## Known Deferred Items

Carried from Phase 9/10/11/12 (see `docs/progress/phase-12-user-accounts-persistent-sessions.md`):

- `guided-flow.spec.ts` default-tab gap (pre-existing since Phase 9/10, unrelated to this phase).
- One pre-existing Ruff formatting exception under `tests/documents/test_documents.py`.

## Phase 13 Known Limitations

- OCR language for the automatic flow defaults to the user's interface language (no
  document-language detection exists) — same limitation Phase 10 already had.
- Orchestration remains synchronous; large/slow documents block the request for their full
  processing time. Background processing is Phase 17's concern.
- The debug/admin field-review route has no additional authentication beyond the existing
  document-ownership check — Phase 14 introduces real admin authentication.
- `review_metadata` does not track per-field AI-translation-fallback usage (see "Decisions and
  Assumptions" above).
