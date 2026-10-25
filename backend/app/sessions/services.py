import re
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.forms.repositories import FormRepository
from app.sessions.models import FormSession
from app.sessions.repositories import SessionRepository
from app.sessions.security import (
    generate_ownership_token,
    hash_ownership_token,
    verify_ownership_token,
)


class ResourceNotFoundError(Exception):
    """Raised when a requested resource is not found."""

    pass


class StateConflictError(Exception):
    """Raised when a state transition or mutation conflicts with current status."""

    pass


class ValidationError(Exception):
    """Raised when business logic validation fails.

    `error_code` is optional so existing call sites that only pass a message
    keep working; set it when the frontend needs to branch on a specific
    machine-readable reason (e.g. "dynamic_pdf_export_not_supported").
    """

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class UnauthorizedError(Exception):
    """Raised when session authentication fails."""

    pass


# Deterministic ISO 639-1 language code check (2-letter lowercase)
ISO_639_1_REGEX = re.compile(r"^[a-z]{2}$")


class SessionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SessionRepository(db)
        self.form_repo = FormRepository(db)

    def create_session(
        self,
        form_version_id: str,
        user_language: str,
        output_language: str,
        current_user_id: str | None = None,
        source_document_id: str | None = None,
    ) -> tuple[FormSession, str]:
        # 1. Fetch form version
        version = self.form_repo.get_version(form_version_id)
        if not version:
            raise ResourceNotFoundError(
                f"Form version with ID '{form_version_id}' not found."
            )
        if version.origin != "predefined_template" and source_document_id is None:
            raise ResourceNotFoundError(
                f"Form version with ID '{form_version_id}' not found."
            )

        # 2. Reject non-published versions
        if version.status != "published":
            raise StateConflictError(
                "Sessions can only be created for published form versions."
            )

        # 3. Validate user language
        if not ISO_639_1_REGEX.match(user_language):
            raise ValidationError(f"Invalid user language code '{user_language}'.")

        # 4. Validate output language is supported by form version
        if output_language not in version.supported_output_languages:
            raise ValidationError(
                f"Output language '{output_language}' "
                "is not supported by this form version."
            )

        # 5. Calculate total required fields count
        total_required = sum(1 for f in version.fields if f.required)

        # 6. Expiration time
        expires_at = datetime.now(UTC) + timedelta(
            hours=settings.FORM_SESSION_TTL_HOURS
        )

        # 7. Security tokens
        raw_token = generate_ownership_token()
        token_hash = hash_ownership_token(raw_token)

        # 8. Create session. A logged-in creator is recorded as the owner
        # immediately (no separate claim needed) — the anonymous token is
        # still generated and returned for API-shape consistency, but
        # get_session() ignores it entirely once user_id is set.
        session = self.repo.create_session(
            form_version_id=form_version_id,
            user_language=user_language,
            source_language=version.source_language,
            output_language=output_language,
            total_required_fields=total_required,
            expires_at=expires_at,
            ownership_token_hash=token_hash,
            user_id=current_user_id,
            source_document_id=source_document_id,
        )

        return session, raw_token

    def get_session(
        self,
        public_id: str,
        raw_token: str | None,
        current_user_id: str | None = None,
    ) -> FormSession:
        """Authorizes access to a session under exactly one of two models:
        anonymous ownership token, or authenticated user. A session's
        `ownership_token_hash` is cleared to NULL the moment it is claimed
        (see app/applications/services.py) — from then on only the owning
        user's `current_user_id` can ever authorize access, and the old
        token is permanently inert. The same generic 401 is returned for
        every failure mode (missing session, wrong token, wrong user) so
        neither path can be used to enumerate sessions or probe ownership.
        """
        session = self.repo.get_session_by_public_id(public_id)
        if not session or session.deleted_at is not None:
            raise UnauthorizedError("Invalid session credentials")

        if session.user_id is not None:
            if not current_user_id or current_user_id != session.user_id:
                raise UnauthorizedError("Invalid session credentials")
        else:
            if not raw_token or not session.ownership_token_hash:
                raise UnauthorizedError("Invalid session credentials")
            if not verify_ownership_token(raw_token, session.ownership_token_hash):
                raise UnauthorizedError("Invalid session credentials")

        # Check and handle expiration first. Claimed (authenticated-owned)
        # sessions never expire merely by crossing their original
        # anonymous-lifetime `expires_at` — persistence for authenticated
        # applications is intentionally not time-boxed the same way.
        now = datetime.now(UTC)
        if (
            session.user_id is None
            and session.expires_at < now
            and session.status not in ("expired", "cancelled", "completed", "failed")
        ):
            session.status = "expired"
            self.db.commit()

        return session

    def start_session(
        self,
        public_id: str,
        raw_token: str | None,
        current_user_id: str | None = None,
    ) -> FormSession:
        session = self.get_session(public_id, raw_token, current_user_id)

        # Already active — idempotent no-op so a repeated/duplicate start
        # request (e.g. React effect re-run) never breaks the UI.
        if session.status == "in_progress":
            return session

        # Expiry or cancelled sessions are terminal
        if session.status == "expired":
            raise StateConflictError("Cannot start an expired session.")
        if session.status == "cancelled":
            raise StateConflictError("Cannot start a cancelled session.")
        if session.status != "session_created":
            raise StateConflictError(
                f"Cannot transition from state '{session.status}' to 'in_progress'."
            )

        session.status = "in_progress"
        self.db.commit()
        return session

    def cancel_session(
        self,
        public_id: str,
        raw_token: str | None,
        current_user_id: str | None = None,
    ) -> FormSession:
        session = self.get_session(public_id, raw_token, current_user_id)

        terminal_statuses = ("expired", "cancelled", "completed", "failed")
        if session.status in terminal_statuses:
            raise StateConflictError(
                f"Cannot cancel session in terminal state '{session.status}'."
            )

        session.status = "cancelled"
        session.cancelled_at = datetime.now(UTC)
        self.db.commit()
        return session

    def cleanup_expired_sessions(self) -> int:
        now = datetime.now(UTC)
        expired_sessions = self.repo.find_expired_sessions(now)
        count = 0
        for s in expired_sessions:
            s.status = "expired"
            count += 1
        if count > 0:
            self.db.commit()
        return count
