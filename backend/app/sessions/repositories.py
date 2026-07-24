from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

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
    ) -> FormSession:
        session = FormSession(
            form_version_id=form_version_id,
            user_language=user_language,
            source_language=source_language,
            output_language=output_language,
            total_required_fields=total_required_fields,
            expires_at=expires_at,
            ownership_token_hash=ownership_token_hash,
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
            .options(joinedload(FormSession.version))
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
