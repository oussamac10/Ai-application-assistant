# ADR 0011 — User Accounts and Persistent Sessions

**Status:** Accepted
**Phase:** 12 — User Accounts and Persistent Sessions
**Date:** 2026-07-27

---

## Context

Every prior phase modeled ownership as a single anonymous, token-owned `FormSession`/`SourceDocument`: a cryptographically random ownership token, HMAC-hashed at rest, is the only thing that ever authorizes access. Phase 12 must add first-party email/password accounts and let a signed-in user save, resume, rename, and delete applications, and claim an anonymous application into their account — without breaking anonymous usage, without inventing a second, incompatible authorization model, and without letting Phase 13 (administration) creep in early.

---

## Decisions

### 1. `FormSession` is the persistent "application" — no separate `Application` aggregate

Ownership in this codebase was already centralized at exactly two root aggregates, `FormSession` and `SourceDocument`. `FormSession` already models id, status, form reference, timestamps, and progress — everything an "application history" entry needs. Introducing a third `Application` aggregate would only create a second source of truth to keep in sync with `FormSession.status` for no behavioral benefit. `FormSession` instead gained `user_id`, `source_document_id`, `title`, `last_opened_at`, and `deleted_at` columns; existing `status` values (including the already-defined `deleted` terminal state from the domain's session state machine) are reused as-is.

### 2. Auth session tokens reuse the exact anonymous ownership-token pattern — not JWTs

`AuthSession.token_hash` is an HMAC-SHA256 hash of a `secrets.token_urlsafe(32)` raw token, verified in constant time — identical in shape to `app/sessions/security.py`'s ownership tokens. The raw token is returned to the client exactly once (as an HttpOnly cookie) and only ever compared by its hash from then on. This was chosen over JWTs because the codebase has no existing token-verification/revocation machinery to extend, and a hash-at-rest opaque token gives trivial, immediate server-side revocation (delete/expire a row) that a stateless JWT would need a separate denylist to replicate anyway.

### 3. Password hashing: Argon2id via `argon2-cffi`

The only hashing dependency already in the repo is HMAC-SHA256 for tokens, which is unsuitable for passwords (too fast, invertible-by-bruteforce with commodity hardware). Argon2id is the current industry-standard password hash and has no comparable existing capability in the codebase, satisfying the dependency-addition rule ("no existing duplicate capability").

### 4. Cookie + CSRF model

The auth session token is stored in an HttpOnly, `SameSite=Lax` cookie (`Secure` in production), unreadable to page JavaScript — this is what makes it resistant to XSS token theft. Because the browser attaches cookies automatically, a separate CSRF defense is required for mutating requests: a second, non-HttpOnly cookie holds a CSRF token that frontend JS reads and echoes back as an `X-CSRF-Token` header (double-submit pattern). `verify_csrf` only enforces this when an auth cookie is present — anonymous, token-header-authenticated requests (the pre-existing model) are unaffected, since a third-party page cannot forge Anonymous ownership tokens either way (they're never stored in a cookie).

A previously-permissive CORS config (`allow_origins=["*"]` with `allow_credentials=True`) is invalid per the CORS spec once cookies are involved — browsers reject the combination outright — so it was replaced with an explicit `ALLOWED_ORIGINS` allowlist (`app/core/config.py`).

### 5. Dual ownership model: exactly one of (ownership token) or (`user_id`) is ever meaningful

`FormSession.ownership_token_hash` and `SourceDocument.ownership_token_hash` became nullable. `SessionService.get_session`, `SourceDocumentService.get_document`, and `PDFExportService._verify_ownership` all check `user_id is not None` first: if set, only a matching authenticated caller may access the resource and the anonymous token is never consulted again; otherwise, the original anonymous-token verification runs unchanged. A session created by an already-authenticated user gets `user_id` set immediately at creation (no separate claim step needed); an anonymous session becomes user-owned only through the explicit claim flow. This is the same generic-401-on-any-failure shape the anonymous model already used, so neither path can be used to enumerate sessions or distinguish "wrong token" from "not found."

### 6. Claiming is atomic, idempotent, and permanently invalidates the old token

`ApplicationService.claim` (`app/applications/services.py`) loads the target session by its public ID, verifies the supplied ownership token against its hash, and — in one transaction — sets `user_id` and clears `ownership_token_hash` to `NULL`. Calling claim again for a session the *same* user already owns is a no-op that returns success (idempotent); calling it for a session owned by a *different* user returns the same generic unauthorized response as an invalid token (no enumeration). Once claimed, the anonymous token can never authorize access again, matching how a leaked or logged token should behave once its owner has moved to a durable account.

### 7. Application history API returns summaries only, never raw tokens or document contents

`GET /applications` and `GET /applications/{id}` return `title`, `status`, `formName`, progress, and timestamps — never `ownership_token_hash`, never document storage paths, never answer content. This follows the same summary-only exposure rule already used for `SessionResponse`/`DocumentRetrieveResponse`.

### 8. Resume must not duplicate sessions or redo AI/OCR/detection work

Because claiming mutates the *existing* `FormSession` row in place rather than creating a new one, resuming a claimed application is just `GET`/`start` against the same session ID the anonymous flow already produced — the existing idempotent `start_session` (Phase 11 fix) and answer/detection state are untouched. The frontend's guided-session and summary pages previously hard-required an anonymous token in `sessionStorage` before making any request; this blocked exactly the case an authenticated resume needs (no token stored at all), so that client-side guard was removed in favor of letting the request itself succeed or fail on the cookie-based authorization the backend now provides.

### 9. Phase 13 (administration) is explicitly out of scope

No admin listing, no cross-user visibility, no account suspension/moderation endpoints were added. `User.status` exists only for the "active" gate `AuthService` already checks (a deactivated account cannot log in or use existing sessions); nothing in Phase 12 sets it to anything else.
