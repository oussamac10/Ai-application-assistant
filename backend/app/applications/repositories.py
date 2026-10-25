from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.forms.models import FormVersion
from app.sessions.models import FormSession


class ApplicationRepository:
    """Read/write access to FormSession rows in their role as a persistent,
    user-owned "application" (see docs/decisions for the Option-B rationale:
    no separate Application aggregate). Every method here is scoped to
    authenticated ownership — anonymous/token-based access stays in
    app/sessions and app/documents."""

    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: str) -> list[FormSession]:
        stmt = (
            select(FormSession)
            .where(FormSession.user_id == user_id, FormSession.deleted_at.is_(None))
            .options(
                joinedload(FormSession.version).joinedload(FormVersion.template),
                joinedload(FormSession.version).joinedload(FormVersion.fields),
            )
            .order_by(FormSession.updated_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_owned(self, user_id: str, public_id: str) -> FormSession | None:
        stmt = (
            select(FormSession)
            .where(
                FormSession.public_id == public_id,
                FormSession.user_id == user_id,
                FormSession.deleted_at.is_(None),
            )
            .options(
                joinedload(FormSession.version).joinedload(FormVersion.template),
                joinedload(FormSession.version).joinedload(FormVersion.fields),
            )
        )
        return self.db.scalars(stmt).unique().first()

    def touch_last_opened(self, session: FormSession, now: datetime) -> None:
        session.last_opened_at = now
        self.db.commit()

    def rename(self, session: FormSession, title: str) -> None:
        session.title = title
        self.db.commit()
        self.db.refresh(session)

    def soft_delete(self, session: FormSession, now: datetime) -> None:
        session.deleted_at = now
        session.status = "deleted"
        self.db.commit()
