from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.errors import (
    AuthConflictError,
    AuthUnauthorizedError,
    AuthValidationError,
)
from app.auth.models import AuthSession, User
from app.auth.repositories import AuthSessionRepository, UserRepository
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

_MAX_PASSWORD_LENGTH = 256
# Precomputed once at import time so unknown-email login attempts perform a
# full Argon2id verification pass and take the same wall-clock time as an
# existing account with an incorrect password.
_DUMMY_PASSWORD_HASH = hash_password("timing-equalizer-placeholder-password-0123456789")


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.auth_sessions = AuthSessionRepository(db)

    def register(self, email: str, password: str, password_confirmation: str) -> User:
        if not is_valid_email(email):
            raise AuthValidationError("Invalid email address.", "invalid_email")

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
        return self.users.create_user(
            email=email,
            normalized_email=normalized,
            password_hash=password_hash,
            role=role,
        )

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
