import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.applications.services import ApplicationService
from app.auth.email_provider import EmailProvider, get_email_provider
from app.auth.errors import (
    AuthConflictError,
    AuthUnauthorizedError,
    AuthValidationError,
)
from app.auth.models import AuthActionToken, AuthSession, User
from app.auth.repositories import (
    AuthActionTokenRepository,
    AuthSessionRepository,
    UserRepository,
)
from app.auth.security import (
    generate_auth_token,
    hash_auth_token,
    hash_password,
    is_valid_email,
    normalize_email,
    verify_auth_token,
    verify_password,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_PASSWORD_LENGTH = 256
# Precomputed once at import time so unknown-email login attempts perform a
# full Argon2id verification pass and take the same wall-clock time as an
# existing account with an incorrect password.
_DUMMY_PASSWORD_HASH = hash_password("timing-equalizer-placeholder-password-0123456789")

PURPOSE_EMAIL_VERIFICATION = "email_verification"
PURPOSE_PASSWORD_RESET = "password_reset"


class AuthService:
    def __init__(
        self,
        db: Session,
        email_provider: EmailProvider | None = None,
    ):
        self.db = db
        self.users = UserRepository(db)
        self.auth_sessions = AuthSessionRepository(db)
        self.action_tokens = AuthActionTokenRepository(db)
        self.email_provider: EmailProvider = (
            email_provider if email_provider is not None else get_email_provider()
        )

    def _validate_password_pair(
        self, password: str, password_confirmation: str
    ) -> None:
        if password != password_confirmation:
            raise AuthValidationError(
                "Password and confirmation do not match.", "password_mismatch"
            )
        if (
            len(password) < settings.PASSWORD_MIN_LENGTH
            or len(password) > _MAX_PASSWORD_LENGTH
        ):
            raise AuthValidationError(
                f"Password must be between {settings.PASSWORD_MIN_LENGTH} and "
                f"{_MAX_PASSWORD_LENGTH} characters.",
                "weak_password",
            )

    def register(self, email: str, password: str, password_confirmation: str) -> User:
        if not is_valid_email(email):
            raise AuthValidationError("Invalid email address.", "invalid_email")

        self._validate_password_pair(password, password_confirmation)

        normalized = normalize_email(email)
        if self.users.get_by_normalized_email(normalized):
            # Message intentionally generic; callers must not use this to
            # distinguish "exists" from other validation failures in a way
            # that lets a client script enumerate accounts at scale — the
            # HTTP layer maps this to the same conflict status either way,
            # never a targeted "email already exists" 200-adjacent hint.
            raise AuthConflictError("Unable to complete registration.")

        password_hash = hash_password(password)
        role = "platform_admin" if normalized in settings.admin_emails_set else "user"
        user = self.users.create_user(
            email=email,
            normalized_email=normalized,
            password_hash=password_hash,
            role=role,
        )
        try:
            self.request_email_verification(user)
        except Exception as exc:
            logger.warning(
                "Initial verification email dispatch failed (%s); user can re-request",
                type(exc).__name__,
            )
        return user

    def _issue_action_token(self, user: User, purpose: str, ttl: timedelta) -> str:
        now = datetime.now(UTC)
        self.action_tokens.invalidate_pending_for_user(user.id, purpose, now)
        raw_token = generate_auth_token()
        token_hash = hash_auth_token(raw_token)
        self.action_tokens.create_token(
            user_id=user.id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=now + ttl,
        )
        return raw_token

    def _verify_and_resolve_action_token(
        self, raw_token: str, expected_purpose: str
    ) -> tuple[AuthActionToken, User]:
        cleaned = (raw_token or "").strip()
        if not cleaned:
            raise AuthValidationError(
                "Invalid or expired token.", "invalid_or_expired_token"
            )
        token_hash = hash_auth_token(cleaned)
        token_row = self.action_tokens.get_by_token_hash(token_hash)
        now = datetime.now(UTC)
        if (
            not token_row
            or token_row.purpose != expected_purpose
            or token_row.consumed_at is not None
            or token_row.expires_at < now
            or not verify_auth_token(cleaned, token_row.token_hash)
        ):
            raise AuthValidationError(
                "Invalid or expired token.", "invalid_or_expired_token"
            )

        user = self.users.get_by_id(token_row.user_id)
        if not user or user.status != "active":
            raise AuthValidationError(
                "Invalid or expired token.", "invalid_or_expired_token"
            )
        return token_row, user

    def request_email_verification(self, user: User) -> None:
        if user.email_verified:
            return
        raw_token = self._issue_action_token(
            user,
            PURPOSE_EMAIL_VERIFICATION,
            timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS),
        )
        self.email_provider.send_email_verification(user.email, raw_token)

    def confirm_email_verification(self, raw_token: str) -> User:
        token_row, user = self._verify_and_resolve_action_token(
            raw_token, PURPOSE_EMAIL_VERIFICATION
        )
        now = datetime.now(UTC)
        self.action_tokens.consume(token_row, now)
        return self.users.mark_email_verified(user, now)

    def request_password_reset(self, email: str) -> None:
        """Anti-enumeration: returns identically whether the email exists or not."""
        if not is_valid_email(email):
            return
        normalized = normalize_email(email)
        user = self.users.get_by_normalized_email(normalized)
        if not user or user.status != "active":
            return
        raw_token = self._issue_action_token(
            user,
            PURPOSE_PASSWORD_RESET,
            timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
        )
        self.email_provider.send_password_reset(user.email, raw_token)

    def confirm_password_reset(
        self,
        raw_token: str,
        password: str,
        password_confirmation: str,
    ) -> None:
        self._validate_password_pair(password, password_confirmation)
        token_row, user = self._verify_and_resolve_action_token(
            raw_token, PURPOSE_PASSWORD_RESET
        )
        now = datetime.now(UTC)
        new_hash = hash_password(password)
        self.action_tokens.consume(token_row, now)
        self.users.update_password_hash(user, new_hash)
        self.auth_sessions.revoke_all_for_user(user.id, now)

    def export_account_data(self, user: User) -> dict[str, Any]:
        app_service = ApplicationService(self.db)
        applications_data, documents_data = (
            app_service.export_user_applications_and_documents(user.id)
        )
        vault_items: list[dict[str, Any]] = []
        try:
            from app.vault.services import ProfileVaultService

            vault_items = ProfileVaultService(self.db).export_for_user(user.id)
        except ImportError:
            vault_items = []

        return {
            "exported_at": datetime.now(UTC),
            "account": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "email_verified": user.email_verified,
                "email_verified_at": user.email_verified_at,
                "created_at": user.created_at,
                "last_login_at": user.last_login_at,
            },
            "profile_vault": vault_items,
            "applications": applications_data,
            "documents": documents_data,
        }

    def delete_account(self, user: User) -> None:
        ApplicationService(self.db).purge_all_for_user(user.id)
        self.users.hard_delete(user)

    def login(self, email: str, password: str) -> tuple[User, str]:
        """Returns (user, raw_auth_token). Raises AuthUnauthorizedError with
        a non-specific message for both unknown email and wrong password —
        never distinguish the two to the caller."""
        normalized = normalize_email(email)
        user = self.users.get_by_normalized_email(normalized)
        if not user or user.status != "active":
            verify_password(password, _DUMMY_PASSWORD_HASH)
            raise AuthUnauthorizedError("Unknown account.")

        if not verify_password(password, user.password_hash):
            raise AuthUnauthorizedError("Incorrect password.")

        if normalized in settings.admin_emails_set and user.role != "platform_admin":
            user.role = "platform_admin"
        user.last_login_at = datetime.now(UTC)
        self.db.commit()

        raw_token = self._issue_session(user.id)
        return user, raw_token

    def _issue_session(self, user_id: str) -> str:
        raw_token = generate_auth_token()
        token_hash = hash_auth_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(
            hours=settings.AUTH_SESSION_TTL_HOURS
        )
        self.auth_sessions.create_session(user_id, token_hash, expires_at)
        return raw_token

    def get_current_user(
        self, raw_token: str | None
    ) -> tuple[User, AuthSession] | None:
        """Returns (user, auth_session) for a valid, non-expired,
        non-revoked token, else None — never raises, so callers can treat
        "no cookie" and "invalid cookie" identically (anonymous)."""
        if not raw_token:
            return None

        token_hash = hash_auth_token(raw_token)
        session = self.auth_sessions.get_by_token_hash(token_hash)
        if not session:
            return None
        if session.revoked_at is not None:
            return None
        if session.expires_at < datetime.now(UTC):
            return None
        # Constant-time re-verification against the stored hash (defense in
        # depth beyond the indexed lookup above, matching the anonymous
        # ownership-token pattern's verify step).
        if not verify_auth_token(raw_token, session.token_hash):
            return None

        user = self.users.get_by_id(session.user_id)
        if not user or user.status != "active":
            return None

        self.auth_sessions.touch_last_used(session, datetime.now(UTC))
        return user, session

    def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        token_hash = hash_auth_token(raw_token)
        session = self.auth_sessions.get_by_token_hash(token_hash)
        if session and session.revoked_at is None:
            self.auth_sessions.revoke(session, datetime.now(UTC))

    def refresh(self, raw_token: str | None) -> tuple[User, str]:
        """Rotates the session token: issues a new one and revokes the
        old one, so a leaked older token stops working going forward."""
        resolved = self.get_current_user(raw_token)
        if not resolved:
            raise AuthUnauthorizedError("Invalid or expired session.")
        user, old_session = resolved

        new_raw_token = self._issue_session(user.id)
        self.auth_sessions.revoke(old_session, datetime.now(UTC))
        return user, new_raw_token
