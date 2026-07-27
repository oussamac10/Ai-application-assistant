# Session Handoff

Replace this content at the end of each substantial session.

## Last completed action

Phase 12 — User Accounts and Persistent Sessions is complete. Resumed from a prior session's in-progress backend scaffolding (models, migration, security module, basic auth service/routes existed but were not wired into `main.py`, had no tests, and the claim/application-history/PDF-export/frontend layers did not exist yet). This session:

1. Registered the auth router, added its exception handlers, and fixed an invalid CORS config (`allow_origins=["*"]` + `allow_credentials=True`, which browsers reject once cookies are used) with an explicit `ALLOWED_ORIGINS` allowlist.
2. Threaded `current_user` (optional) through documents routes/service and PDF export routes/service, extending the same dual-ownership authorization model already present in `SessionService` — export would otherwise have been permanently broken for any claimed session.
3. Built `app/applications/` from scratch: atomic/idempotent claim endpoint, and list/detail/rename/delete application-history API, reusing `FormSession` as the persistent "application" (no new aggregate).
4. Added `backend/tests/auth/` (10 tests) and `backend/tests/applications/` (17 tests) — register/login/logout/me/refresh, password hashing, claim idempotency/IDOR, rename/delete, cross-user isolation.
5. Built the full frontend: `features/auth/` (AuthProvider, LoginForm, RegisterForm, AccountMenu), `features/applications/` (ApplicationCard, ClaimBanner, applicationsClient), `/login`, `/register`, `/applications` pages, and removed a client-side guard on the guided-session/summary pages that hard-blocked resuming a claimed session (no anonymous token in `sessionStorage`).
6. Added `auth`/`applications` translation namespaces to all four `messages/*.json` files.
7. Added 8 new Vitest unit tests and 3 new Playwright specs (register→session→resume/rename/delete; anonymous→claim→resume; Arabic RTL on the new pages).
8. Wrote ADR 0011, `docs/user-accounts.md`, and updated `docs/security.md`/`docs/privacy.md`/`docs/claude/architecture-map.md`.
9. Ran the full verification pass locally via `backend/venv/bin/python` (not Docker, per this session's instructions) — see `TODO.md` "Verification" for exact results, including bugs found and fixed during that pass.

## Repository state

- Branch: `feature/user-accounts-persistent-sessions` (base: `feature/dynamic-field-detection`)
- Docker Compose backend image was rebuilt this session (it was crash-looping on a stale image missing `argon2-cffi`); now healthy.
- The local Postgres dev database's `basic-registration` fixture was re-seeded (`python -m app.commands.load_fixture`) after the backend pytest suite's `TRUNCATE` cleanup wiped it — needed for Playwright.

## Files changed (Phase 12, cumulative across both sessions)

Backend: `app/auth/*` (new), `app/applications/*` (new), `app/main.py`, `app/core/config.py`, `app/sessions/{models,services,repositories,api/routes}.py`, `app/documents/{models,service,api/routes}.py`, `app/answers/{services,api/routes}.py`, `app/pdf/{services,api/routes}.py`, `backend/migrations/env.py`, `backend/migrations/versions/c24721b9eaee_*.py`, `backend/requirements.txt`, `backend/tests/auth/*`, `backend/tests/applications/*`.

Frontend: `src/features/auth/*` (new), `src/features/applications/*` (new), `src/app/{login,register,applications}/page.tsx` (new), `src/app/layout.tsx`, `src/app/application/session/[sessionId]/{page.tsx,summary/page.tsx}`, `src/features/form-session/services/apiClient.ts`, `src/features/form-session/tests/guided-session-{multiple-choice,translation}.test.tsx` (auth mock added), `messages/{en,de,fr,ar}.json`, `e2e/user-accounts-persistent-sessions-flow.spec.ts` (new), `e2e/user-accounts-rtl-check.spec.ts` (new).

Docs: `docs/decisions/0011-user-accounts-persistent-sessions.md` (new), `docs/user-accounts.md` (new), `docs/security.md`, `docs/privacy.md`, `docs/claude/architecture-map.md`, `docs/claude/current-phase.md`, `TODO.md`, this file.

Docker: `.env.example` (`OCR_PROVIDER=local`, pre-existing carried change), `docker-compose.yml` (pre-existing carried changes for `OCR_PROVIDER`/`FIELD_DETECTION_PROVIDER`/`AI_PROVIDER`/Ollama passthrough).

## Verification results

See `TODO.md`'s "Verification" section for exact pass/fail counts (backend: 304 passed; frontend: 77 passed; Playwright: 15 passed / 11 skipped / 1 pre-existing unrelated failure) and the list of bugs found and fixed during this phase's own verification pass.

## Known limitation carried forward

- `guided-flow.spec.ts`'s default-tab mismatch (pre-existing since Phase 9, unrelated to Phase 12).
- No password reset / email verification / MFA (explicitly out of scope for Phase 12).

## Next action

Phase 12 is done. Do not start Phase 13 (administration and content review) until explicitly requested. If asked to close Phase 12 (mirroring how Phase 10/11 were closed): archive this TODO under `docs/progress/phase-12-user-accounts-persistent-sessions.md`, reset root `TODO.md`, and update `docs/claude/current-phase.md` to "no active phase."

## Blockers

None.

## Decisions

See ADR 0011 (`docs/decisions/0011-user-accounts-persistent-sessions.md`) for the full architectural rationale (persistent-application modeling, auth token pattern, password hashing choice, cookie/CSRF model, dual-ownership authorization, claim semantics, resume-without-duplication). Additional decisions made resolving issues found during this session's verification pass are recorded in `TODO.md`'s "Decisions and Assumptions" and "Bugs found and fixed" subsections.
