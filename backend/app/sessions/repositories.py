from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.forms.models import FormVersion
from app.sessions.models import FormSession


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        form_version_id: str,
        user_language: str,
        source_language: str,
        output_language: str,
        total_required_fields: int,
        expires_at: datetime,
        ownership_token_hash: str,
        user_id: str | None = None,
        source_document_id: str | None = None,
    ) -> FormSession:
        session = FormSession(
            form_version_id=form_version_id,
            user_language=user_language,
            source_language=source_language,
            output_language=output_language,
            total_required_fields=total_required_fields,
            expires_at=expires_at,
            ownership_token_hash=ownership_token_hash,
            user_id=user_id,
            source_document_id=source_document_id,
            status="session_created",
            current_field_position=0,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session_by_public_id(self, public_id: str) -> FormSession | None:
        stmt = (
            select(FormSession)
            .where(FormSession.public_id == public_id)
            .options(
                joinedload(FormSession.version).joinedload(FormVersion.fields),
                selectinload(FormSession.answers),
            )
        )
        return self.db.scalars(stmt).unique().first()

    def get_session_by_id(self, session_id: str) -> FormSession | None:
        stmt = (
            select(FormSession)
            .where(FormSession.id == session_id)
            .options(
                joinedload(FormSession.version).joinedload(FormVersion.fields),
                selectinload(FormSession.answers),
            )
        )
        return self.db.scalars(stmt).unique().first()

    def get_latest_session_by_source_document_id(
        self, source_document_id: str
    ) -> FormSession | None:
        """Used for orchestration idempotency (Phase 13): a repeated
        prepare-questions request for the same document must never create a
        second session. Only non-retryable (live or completed) sessions
        block recreation — cancelled/failed sessions allow a fresh attempt."""
        stmt = (
            select(FormSession)
            .where(FormSession.source_document_id == source_document_id)
            .where(FormSession.deleted_at.is_(None))
            .order_by(FormSession.created_at.desc())
        )
        return self.db.scalars(stmt).first()

    def find_expired_sessions(self, now: datetime) -> list[FormSession]:
        # Expired means expires_at is past now AND status is not terminal
        # Terminal statuses for cleanup: expired, cancelled, completed
        terminal_statuses = ["expired", "cancelled", "completed", "failed"]
        stmt = (
            select(FormSession)
            .where(FormSession.expires_at < now)
            .where(FormSession.status.not_in(terminal_statuses))
        )
        return list(self.db.scalars(stmt).all())
