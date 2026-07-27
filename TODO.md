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

---

## Current Task

**Phase 12 — User Accounts and Persistent Sessions.** Branch: `feature/user-accounts-persistent-sessions`. Base: `feature/dynamic-field-detection`. **Status: Complete.**

## Goal

Add secure first-party email/password user accounts and persistent applications on top of the existing anonymous, token-owned session model — without breaking anonymous usage. Authenticated users can save, resume, rename, and delete applications, and claim an anonymous application into their account. Phase 13 (administration and content review) is explicitly out of scope.

See `docs/phases/phase-12-user-accounts-persistent-sessions.md` for the full specification.

## Acceptance Criteria

- [x] `User` model + Argon2id password hashing, never plaintext/reversible
- [x] `AuthSession` (refresh/session token) model, HMAC-hashed at rest, mirroring the existing ownership-token pattern
- [x] Register / login / logout / me / refresh endpoints, generic error responses (no account enumeration)
- [x] Secure HttpOnly, SameSite, (prod) Secure auth cookie; CSRF protection for cookie-authenticated mutations
- [x] `FormSession`/`SourceDocument` extended with nullable `user_id` — anonymous ownership path fully preserved
- [x] Atomic, idempotent anonymous-application claim endpoint; old ownership token invalidated after claim
- [x] One consistent authorization layer; no IDOR; same not-found/unauthorized behavior as existing ownership checks
- [x] Application history API (list/detail/rename/delete) with safe summary-only list responses
- [x] Frontend: register, login, logout, account menu, My Applications, resume, rename, delete — en/de/fr/ar, RTL preserved
- [x] Resume reuses existing session/answer state — no duplicate sessions, no re-running OCR/detection/AI translation unnecessarily
- [x] Reversible Alembic migration; anonymous data unaffected by upgrade
- [x] `pytest-asyncio` added to `requirements.txt`; async tests no longer silently skip in a clean Docker image
- [x] Backend, frontend, and Playwright tests per the test plan
- [x] ADR for auth/session architecture; `docs/user-accounts.md` user-facing docs; privacy/security docs updated

## Planned Steps

- [x] Phase initialization and documentation
- [x] `User`/`AuthSession` models + migration
- [x] Password hashing + auth token security module (mirrors `app/sessions/security.py`)
- [x] Auth service + API routes + cookie/CSRF handling
- [x] Ownership extension (`user_id` on `FormSession`/`SourceDocument`) + migration
- [x] Authorization dependency usable by both anonymous-token and authenticated-user paths (sessions, documents, PDF export)
- [x] Claim flow (service + endpoint + tests)
- [x] Application history API (list/detail/rename/delete)
- [x] Frontend auth pages + My Applications + claim prompt (4 languages, RTL)
- [x] Resume-state verification (no duplicate work; removed a client-side guard that blocked cookie-only resume)
- [x] Backend/frontend/Playwright test suites
- [x] Documentation, `.env.example`, full verification pass

## Decisions and Assumptions

- `FormSession` is extended in place to serve as the persistent "application" (Option B) rather than introducing a separate `Application` aggregate — `FormSession` already models id, status, form reference, timestamps, and progress; ownership today is already centralized at exactly two root aggregates (`FormSession`, `SourceDocument`), so duplicating that into a third aggregate would only create sync risk without a clear benefit.
- Existing `FormSession.status` values are reused as-is; no new status vocabulary is introduced for "application" state.
- Auth session tokens follow the exact same HMAC-SHA256-hash-at-rest, one-time-exposure pattern already used for anonymous ownership tokens (`app/sessions/security.py`), not JWTs — consistent with the codebase's existing security model and avoiding a new class of token-validation logic.
- Argon2id via `argon2-cffi` for password hashing (industry-standard, no existing hashing dependency in the repo to reuse).
- `pytest-asyncio` is added to `requirements.txt` as part of this phase, fixing a pre-existing dependency-tracking gap documented since Phase 5/6 verification passes.
- `allow_origins=["*"]` combined with `allow_credentials=True` (pre-existing CORS config) is invalid once cookies are involved — browsers reject the combination per the CORS spec. Replaced with an explicit `ALLOWED_ORIGINS` allowlist setting (default: `http://localhost:3000,http://localhost:3003`, the two known local dev origins).
- Application soft-delete reuses the existing `deleted` terminal session status from the domain's documented session state machine (`docs/claude/domain-rules.md`) rather than inventing a new status value; a deleted session is excluded from `GET /applications` and rejected (generic 401, same as any unauthorized access) by `SessionService.get_session`.
- The claim endpoint accepts an optional `documentId`/`documentToken` pair to best-effort also claim the session's linked `SourceDocument` under the same user; if that token is absent or doesn't verify, only the session itself is claimed — this is intentionally silent (non-fatal) since the document isn't required for the guided session/answer/export flow to keep working.

## Blockers

- None identified before implementation.

## Verification

All commands run locally via `backend/venv/bin/python` (not Docker) against the same Postgres instance the Docker stack uses, per session instructions:

- `venv/bin/python -m ruff check .` → All checks passed.
- `venv/bin/python -m ruff format --check .` → 8 pre-existing files would reformat (`app/documents/*.py` and `tests/documents/test_documents.py`, documented since Phase 10, untouched); all other 157 files already formatted.
- `venv/bin/python -m mypy app` → Success: no issues found in 128 source files.
- `PYTHONPATH=. venv/bin/python -m pytest -q` → **304 passed**, 0 failed, 0 skipped (includes 27 new Phase 12 tests: 10 in `tests/auth/`, 17 in `tests/applications/`).
- `venv/bin/python -m alembic downgrade -1` then `upgrade head` → clean round-trip; full suite re-verified passing after.
- `cd frontend && npm run typecheck` → clean (`tsc --noEmit`, no output).
- `npm run lint` → "No ESLint warnings or errors".
- `npm test` → **77 passed** (0 failed), including 8 new Phase 12 tests (`LoginForm`/`RegisterForm`, My Applications page list/rename/delete/redirect).
- `PLAYWRIGHT_BASE_URL=http://localhost:3003 npx playwright test` (against the rebuilt Docker frontend, backend rebuilt with `argon2-cffi`/`pytest-asyncio` present) → **15 passed**, 11 skipped (pre-existing: require live Ollama/local OCR/field-detection providers, unrelated to this phase), **1 failed**: `guided-flow.spec.ts` — pre-existing gap (the landing page's default tab is "Upload Form"; that spec never clicks "Select Manually" before looking for `#form-select`), tracked since Phase 9/10, not a Phase 12 regression. All 3 new Phase 12 specs pass (`user-accounts-persistent-sessions-flow.spec.ts` ×2, `user-accounts-rtl-check.spec.ts`).

### Bugs found and fixed during this phase's own verification (not present before Phase 12's changes)

- `PDFExportService`/`app/pdf/api/routes.py` did not know about the new dual-ownership model (`ownership_token_hash` became nullable), which would have permanently broken PDF export for any claimed session. Extended `_verify_ownership`/`create_export` to the same dual-ownership check used by `SessionService`/`SourceDocumentService`, and made the `X-Session-Token` header optional on both export endpoints.
- The guided-session and summary frontend pages hard-blocked on a missing anonymous `sessionStorage` token before making any request — which is exactly the state a claimed (authenticated-owned) session resume is in. Removed the client-side guard; the request itself now succeeds via the auth cookie or fails with the normal error state.
- `frontend/src/app/applications/page.tsx`'s initial load effect depended on `router` and a callback re-created each render; because the mocked `useRouter()` in tests (and, in principle, any consumer re-creating a router reference) is not guaranteed stable, this caused a refetch loop that silently reverted an in-flight rename/delete. Fixed by removing the unstable dependencies from the effect.
- Backend test setup: recreating `TestClient(app)` as a context manager per test (`with TestClient(app) as c`) was destabilizing the shared SQLAlchemy connection pool and leaving `idle in transaction` connections that blocked subsequent `TRUNCATE` calls in local test runs. Switched to one module-level `TestClient(app)` instance per test file (matching the existing `tests/sessions/test_sessions.py` pattern), with cookies cleared per test instead.
- A test fixture (`published_form_version` in `tests/applications/test_applications.py`) called `service.publish_version()` on a version with no fields, which raises — since the fixture had no `try/finally`, the `SessionLocal()` connection was never closed, leaking an open transaction that blocked later tests' `TRUNCATE`. Fixed by adding a required field before publishing and wrapping the fixture body in `try/finally`.

### Environment note

The Docker `backend` container was found crash-looping (`ModuleNotFoundError: No module named 'argon2'`) at the start of this phase's work — its image predated the `requirements.txt` changes already staged from a previous session. Rebuilt (`docker compose build backend && docker compose up -d backend`); now healthy.

## Post-completion bug fix: field-detection/OCR/document authorization regression

Real usage after this phase's initial completion surfaced `401 Unauthorized` on `GET /api/source-documents/{id}/field-detection` (and, by the same root cause, the OCR and document-analysis endpoints, and the field-detection-confirmed-fields session-creation endpoint) for any document created while authenticated, or belonging to a claimed application.

**Root cause:** `app/field_detection/service.py` and `app/ocr/service.py` were never updated for the Phase 12 dual-ownership model — they called `SourceDocumentService.get_document(document_id, token)` with no `current_user_id`, so any document with `user_id` set (created while logged in, or claimed) was unreachable via the auth cookie; only the original anonymous token could ever work, and once claimed, that token was invalidated with no replacement path. Separately, `ApplicationService.claim` only transferred document ownership if the frontend supplied a second `document_token` — which it never does — so claiming a session never actually claimed its linked document at all, leaving field-detection/OCR permanently anonymous-only even after a successful claim.

**Fix:**
- `FieldDetectionService`/`OCRService` gained a `current_user_id` constructor parameter, threaded into every `get_document` call and into `create_session_from_confirmed_fields` (which now also sets `source_document_id`/`current_user_id` on the created session, matching `SourceDocumentService.create_session_from_document`).
- All 5 field-detection routes and both OCR routes now accept `current_user: User | None = Depends(get_current_user_optional)` and an optional (not required) `X-Document-Token` header.
- `ApplicationService.claim` now transfers the linked `SourceDocument`'s ownership unconditionally (once the session's own token has verified) rather than requiring a separate, never-sent document token — the document's ownership was already validated server-side at the moment the session was created from it, so that trust carries forward.

**Tests:** `backend/tests/field_detection/test_field_detection_authorization.py` (8 new tests) — anonymous with/without token, authenticated owner/non-owner, logged-in-but-unclaimed (token still required), claim transfers ownership + invalidates old token, rejected claim never mutates ownership. Full suite: 312 passed (was 304); ruff/mypy clean; frontend 77 passed unaffected; Playwright 15 passed/11 skipped/1 pre-existing unrelated failure, unchanged.

**Files changed:** `app/field_detection/service.py`, `app/field_detection/api/routes.py`, `app/field_detection/question_bridge.py`, `app/ocr/service.py`, `app/ocr/api/routes.py`, `app/applications/services.py`, `.env.example` (documented the previously-undocumented `AUTH_*`/`ALLOWED_ORIGINS` settings), new test file above.

---

## Next Phases (not yet started)

| Phase | Description |
|---|---|
| **13** | Administration and content review |

---

## Known Deferred Items

Carried from Phase 9/10/11:

- `guided-flow.spec.ts` fails against a fresh dev environment: the landing page's default tab is "Upload Form", but that spec never clicks "Select Manually" before looking for `#form-select`. Pre-existing since the upload feature (Phase 9) changed the default tab; not touched in Phase 12 since it's unrelated to accounts/persistence.
- Full repository Ruff formatting still includes one pre-existing formatting issue under `tests/documents/test_documents.py`, predating Phase 10, intentionally left unchanged.
- The local `.env.example`/`docker-compose.yml` `OCR_PROVIDER=local`, `FIELD_DETECTION_PROVIDER=local`, and `AI_PROVIDER=ollama` overrides (pre-existing, intentionally untouched) make a number of Playwright specs that expect the mock providers report as `skipped` rather than run against real Tesseract/Ollama — not a defect in any completed phase's code.

## Phase 12 Known Limitations

- No password reset, email verification, or multi-factor authentication — out of scope for this phase.
- The claim flow's best-effort `SourceDocument` claiming requires the frontend to still hold the document's own ownership token; if that token was already lost (e.g. a different tab), only the `FormSession` itself is claimed. The guided session/answer/export flow does not depend on document access after initial creation, so this has no functional impact on resuming.
