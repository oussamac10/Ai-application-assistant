# Current Phase

## Phase

Phase 12 - User Accounts and Persistent Sessions

## Branch

`feature/user-accounts-persistent-sessions`

## Base

`feature/dynamic-field-detection`

## Objective

Add secure first-party email/password user accounts and persistent applications on top of the existing anonymous, token-owned session model — without breaking anonymous usage. Authenticated users can save, resume, rename, and delete applications, and claim an anonymous application into their account.

## Reuse

- `FormSession` as the persistent "application" (no separate aggregate) — Phase 3
- anonymous ownership-token hashing pattern (`app/sessions/security.py`) reused for auth session tokens
- existing session/answer/PDF-export workflow, completely unmodified in shape

## In scope

- `User`/`AuthSession` models + Argon2id password hashing + migration
- register/login/logout/me/refresh endpoints, generic error responses
- HttpOnly auth cookie + CSRF double-submit protection; explicit CORS allowlist
- `FormSession`/`SourceDocument` extended with nullable `user_id` (dual ownership model)
- atomic, idempotent anonymous-application claim endpoint
- application history API (list/detail/rename/delete), summary-only responses
- frontend: register, login, logout, account menu, My Applications, resume, rename, delete, claim prompt — en/de/fr/ar, RTL preserved
- `pytest-asyncio` added to `requirements.txt`
- backend/frontend/Playwright tests, ADR 0011, `docs/user-accounts.md`

## Out of scope

- Phase 13 (administration and content review)
- password reset / email verification flows
- multi-factor authentication
- OAuth/social login

## Status

Complete. All in-scope items implemented and verified — see root `TODO.md` "Verification" section for exact check results, including the one pre-existing environment-specific exception unrelated to Phase 12 (the `guided-flow.spec.ts` fixture/tab-default gap carried since Phase 9/10).

See `docs/user-accounts.md` for the user guide and `docs/decisions/0011-user-accounts-persistent-sessions.md` for the architecture decisions.
