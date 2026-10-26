# Phase S2 — Account Lifecycle, GDPR Art. 17/20, Encrypted Profile Vault & Dual-Pane Verification Studio

**Status:** Completed & Verified (`2026-10-26`)

## Summary of Changes

1. **`S2-01` Account Lifecycle & GDPR Art. 17/20 Self-Service Controls**:
   - Added `EmailProvider` Protocol (`backend/app/auth/email_provider.py`) with `MockEmailProvider` (test-inspectable in-memory outbox) and `PostmarkEmailProvider` (`X-Postmark-Server-Token` header, zero-PII/zero-token logging).
   - Added `User.email_verified_at` and `auth_action_tokens` table via Alembic migration `c3d4e5f6a7b8_add_auth_action_tokens_phase_s2.py`, storing only single-use `HMAC-SHA256` token hashes.
   - Added `POST /api/auth/verify-email/request`, `POST /api/auth/verify-email/confirm`, `POST /api/auth/password-reset/request` (anti-enumeration `202`), and `POST /api/auth/password-reset/confirm` (rotates Argon2id hash and revokes all active `AuthSession`s).
   - Upgraded `DELETE /api/applications/{id}` and added `DELETE /api/auth/me` to execute full hard-delete cascades across PostgreSQL (`FormExport`, `FormAnswer`, `FormSession`, unreferenced `SourceDocument` + child OCR/detection/usage/job rows, orphaned `dynamic_detection` templates, `UserProfileEntry`, `User`) and `StorageProvider` blobs (`source_documents` & `form_exports`).
   - Added `GET /api/auth/me/export` (`Cache-Control: no-store`) exporting portable JSON (`account`, decrypted `profileVault`, `applications` + `answers`, `documents` metadata) with zero secret hashes, storage paths, or biometric signature strokes.

2. **`S2-02` Encrypted Personal Profile Vault & 1-Click Session Pre-Fill**:
   - Added `backend/app/vault/` (`models.py`, `crypto.py`, `errors.py`, `schemas.py`, `repositories.py`, `services.py`, `api/routes.py`) and Alembic migration `d4e5f6a7b8c9_add_user_profile_entries_phase_s2.py` (`user_profile_entries`).
   - Encrypts canonical JSON payloads at rest via `cryptography.fernet.Fernet` (`VAULT_ENCRYPTION_KEY` when set, otherwise domain-separated `SHA-256("profile-vault-v1:" + AUTH_SECRET)`), deterministically validates values (including IBAN `mod-97`), and rejects biometric `signature` payloads.
   - Added `GET/PUT/DELETE /api/profile-vault*`, opt-in `POST /api/form-sessions/{session_id}/save-to-vault`, and `POST /api/form-sessions/{session_id}/prefill-from-vault` (sets pre-filled answers to `status="awaiting_confirmation"` and `confirmed_by_user=False`, skips already-answered fields, and never silently transliterates personal names across scripts).

3. **`S2-03` Dual-Pane Verification Studio & Cross-Field Consistency Warnings**:
   - Added deterministic cross-field evaluator `backend/app/answers/consistency.py` localized in `en`, `de`, `fr`, and `ar` (`birth_date_in_future`, `move_in_before_birth_date`, `end_date_before_start_date`, `postal_code_country_mismatch`) and extended `GET /api/form-sessions/{session_id}/summary` with `source_label`, session languages (`source_language`, `user_language`, `output_language`), `export_supported`, and `consistency_warnings`.
   - Upgraded `frontend/src/app/application/session/[sessionId]/summary/page.tsx` into the Dual-Pane Verification Studio (4-column multilingual comparison with `<bdi>` RTL isolation, quick-jump consistency warning panel, side-by-side embedded watermarked PDF preview pane, and opt-in Save to Vault), added 1-click Vault Pre-Fill & confirmation in `[sessionId]/page.tsx` (removing all PII console logs), and built `/account`, `/verify-email`, and `/reset-password` localized across `en`, `de`, `fr`, and `ar`.

## Verification Results

- Backend (`ruff check .`, `ruff format --check .`, `mypy app` across `199` source files): **Passed (`0` errors)**
- Alembic migrations (`c3d4e5f6a7b8`, `d4e5f6a7b8c9`) on `ai_form_assistant` and `ai_form_assistant_test`: **Applied cleanly**
- Backend isolated `pytest` (`ai_form_assistant_test` DB, mock AI/translation/email providers): **`1,190 passed, 1 skipped, 0 failed`**
- Frontend (`npm run typecheck`, `npm run lint`, `npx vitest run`): **`31/31` test files (`253/253` tests passed)**
