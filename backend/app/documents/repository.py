from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.models import SourceDocument


class SourceDocumentRepository:
    def create(self, db: Session, doc: SourceDocument) -> SourceDocument:
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    def get_by_public_id(self, db: Session, public_id: str) -> SourceDocument | None:
        stmt = select(SourceDocument).where(SourceDocument.public_id == public_id)
        return db.scalars(stmt).first()

    def get_by_id(self, db: Session, id_val: str) -> SourceDocument | None:
        stmt = select(SourceDocument).where(SourceDocument.id == id_val)
        return db.scalars(stmt).first()

    def get_expired(self, db: Session, current_time: datetime) -> list[SourceDocument]:
        # Excludes already deleted or expired statuses from double deletions
        stmt = select(SourceDocument).where(
            SourceDocument.expires_at <= current_time,
            SourceDocument.status.not_in(["deleted", "expired"]),
        )
        return list(db.scalars(stmt).all())

    def update(self, db: Session, doc: SourceDocument) -> SourceDocument:
        db.commit()
        db.refresh(doc)
        return doc
