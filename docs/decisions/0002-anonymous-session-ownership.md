# Architectural Decision Record (ADR) 0002: Anonymous Session Ownership

## Context

The system must support temporary, anonymous form sessions for users without requiring them to register accounts or store personal identification data permanently. However, these sessions must remain secure:
1. Only the creator of the session should have read/write access to the session's progress and details.
2. Attackers must not be able to guess session IDs or access other users' data.
3. Raw authorization credentials must never be stored in the database to prevent exposure in the event of a database dump or compromise.
4. The system must prevent session enumeration and timing attacks.

## Decision

We implement an anonymous, token-based session ownership validation system:

1. **Dual Identifiers**: 
   - Each session has an internal primary key `id` (UUID v4) and a separate `public_id` (UUID v4). All client-facing endpoints refer exclusively to the `public_id`.
2. **One-Time Token Exposure**:
   - During session creation (`POST /api/form-versions/{id}/sessions`), the backend generates a cryptographically secure random token (`secrets.token_urlsafe(32)`).
   - This raw token is returned *exactly once* in the creation response payload (`ownershipToken`) and is never returned by the API again.
3. **HMAC-SHA256 Hashing at Rest**:
   - The database stores only the HMAC-SHA256 hash of the ownership token, computed using a server-side secret key (`SESSION_TOKEN_SECRET`).
   - Reversible encryption or raw storage is strictly prohibited.
4. **Header Authentication**:
   - For all session-specific read/write requests, the client must send the raw token in the `X-Session-Token` header.
   - The backend hashes the header token and compares it to the database record using constant-time string comparison (`hmac.compare_digest`) to prevent timing attacks.
5. **Generic Error Responses**:
   - If the token is invalid or missing, the backend returns HTTP `401 Unauthorized` with the generic response `{"detail": "Invalid session credentials"}`. 
   - This error is returned regardless of whether the requested session `public_id` exists, preventing session scanning/enumeration.

## Alternatives Considered

### 1. Simple UUID in URL as Auth
- **Pros**: Easy to implement.
- **Cons**: Anyone with access to the URL or browser history can access the session. UUIDs might be logged by proxy servers or CDN layers. No secondary secret verification.

### 2. Full Account System (JWT/OAuth)
- **Pros**: Robust user identity.
- **Cons**: Violates privacy guidelines (requires email, password, profile data) and is out of scope for the MVP Phase 1-3.

## Status

Approved.

## Consequences

- Clients must store the `ownershipToken` locally (e.g., in memory or session storage) immediately upon creation. If lost, the session is unrecoverable.
- Secure configuration management is required to load `SESSION_TOKEN_SECRET` in production environments.
- API route handlers remain thin, deferring authorization and token hashing to the service layer.
