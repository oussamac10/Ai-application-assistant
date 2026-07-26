from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ocr.models import OCRPage, OCRResult


class OCRRepository:
    def create(self, db: Session, result: OCRResult) -> OCRResult:
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    def get_by_source_document_id(
        self, db: Session, source_document_id: str
    ) -> OCRResult | None:
        stmt = (
            select(OCRResult)
            .options(selectinload(OCRResult.pages))
            .where(OCRResult.source_document_id == source_document_id)
        )
        return db.scalars(stmt).first()

    def get_by_public_id(self, db: Session, public_id: str) -> OCRResult | None:
        stmt = (
            select(OCRResult)
            .options(selectinload(OCRResult.pages))
            .where(OCRResult.public_id == public_id)
        )
        return db.scalars(stmt).first()

    def get_expired(self, db: Session, current_time: datetime) -> list[OCRResult]:
        stmt = select(OCRResult).where(
            OCRResult.expires_at <= current_time,
            OCRResult.status.not_in(["deleted", "expired"]),
        )
        return list(db.scalars(stmt).all())

    def update(self, db: Session, result: OCRResult) -> OCRResult:
        db.commit()
        db.refresh(result)
        return result

    def replace_pages(
        self, db: Session, result: OCRResult, pages: list[OCRPage]
    ) -> OCRResult:
        for existing_page in list(result.pages):
            db.delete(existing_page)
        db.flush()
        for page in pages:
            page.ocr_result_id = result.id
            db.add(page)
        db.commit()
        db.refresh(result)
        return result
