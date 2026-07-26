from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.field_detection.models import DetectedField, FieldDetectionResult


class FieldDetectionRepository:
    def create(self, db: Session, result: FieldDetectionResult) -> FieldDetectionResult:
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    def get_by_source_document_and_version(
        self, db: Session, source_document_id: str, analysis_version: int
    ) -> FieldDetectionResult | None:
        stmt = (
            select(FieldDetectionResult)
            .options(
                selectinload(FieldDetectionResult.fields).selectinload(
                    DetectedField.options
                )
            )
            .where(
                FieldDetectionResult.source_document_id == source_document_id,
                FieldDetectionResult.analysis_version == analysis_version,
            )
        )
        return db.scalars(stmt).first()

    def get_by_public_id(
        self, db: Session, public_id: str
    ) -> FieldDetectionResult | None:
        stmt = (
            select(FieldDetectionResult)
            .options(
                selectinload(FieldDetectionResult.fields).selectinload(
                    DetectedField.options
                )
            )
            .where(FieldDetectionResult.public_id == public_id)
        )
        return db.scalars(stmt).first()

    def update(self, db: Session, result: FieldDetectionResult) -> FieldDetectionResult:
        db.commit()
        db.refresh(result)
        return result

    def replace_fields(
        self, db: Session, result: FieldDetectionResult, fields: list[DetectedField]
    ) -> FieldDetectionResult:
        for existing_field in list(result.fields):
            db.delete(existing_field)
        db.flush()
        for detected_field in fields:
            detected_field.detection_result_id = result.id
            db.add(detected_field)
        db.commit()
        db.refresh(result)
        return result

    def get_field_by_public_id(
        self, db: Session, field_public_id: str
    ) -> DetectedField | None:
        stmt = select(DetectedField).where(DetectedField.public_id == field_public_id)
        return db.scalars(stmt).first()

    def update_field(self, db: Session, field: DetectedField) -> DetectedField:
        db.commit()
        db.refresh(field)
        return field
