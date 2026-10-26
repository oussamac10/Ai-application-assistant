from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.answers.models import FormAnswer
from app.documents.models import SourceDocument
from app.field_detection.models import (
    DetectedField,
    DetectedFieldOption,
    FieldDetectionResult,
)
from app.field_detection.usage import ProviderUsageRecord
from app.forms.models import FormTemplate, FormVersion
from app.jobs.models import ProcessingJob
from app.ocr.models import OCRPage, OCRResult
from app.pdf.models import FormExport
from app.sessions.models import FormSession
from app.storage import factory as storage_factory


def _purge_storage_blob(storage_path: str | None) -> None:
    if not storage_path:
        return
    provider = storage_factory.get_storage_provider()
    try:
        if provider.delete(storage_path):
            return
    except Exception:
        pass
    if not storage_path.startswith("s3://"):
        filepath = Path(storage_path)
        try:
            if filepath.is_file():
                filepath.unlink()
        except OSError:
            pass


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

    def list_all_sessions_for_user_including_deleted(
        self, user_id: str
    ) -> list[FormSession]:
        stmt = (
            select(FormSession)
            .where(FormSession.user_id == user_id)
            .options(
                joinedload(FormSession.version).joinedload(FormVersion.template),
                joinedload(FormSession.version).joinedload(FormVersion.fields),
            )
            .order_by(FormSession.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_owned_documents(self, user_id: str) -> list[SourceDocument]:
        stmt = (
            select(SourceDocument)
            .where(SourceDocument.user_id == user_id)
            .order_by(SourceDocument.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_answers_for_session(self, session_id: str) -> list[FormAnswer]:
        stmt = (
            select(FormAnswer)
            .where(FormAnswer.session_id == session_id)
            .options(joinedload(FormAnswer.field))
        )
        return list(self.db.scalars(stmt).all())

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

    def _purge_document_and_children(self, doc: SourceDocument) -> None:
        _purge_storage_blob(doc.storage_path)

        det_ids = list(
            self.db.scalars(
                select(FieldDetectionResult.id).where(
                    FieldDetectionResult.source_document_id == doc.id
                )
            ).all()
        )
        if det_ids:
            field_ids = list(
                self.db.scalars(
                    select(DetectedField.id).where(
                        DetectedField.detection_result_id.in_(det_ids)
                    )
                ).all()
            )
            if field_ids:
                self.db.execute(
                    delete(DetectedFieldOption).where(
                        DetectedFieldOption.detected_field_id.in_(field_ids)
                    )
                )
                self.db.execute(
                    delete(DetectedField).where(DetectedField.id.in_(field_ids))
                )
            self.db.execute(
                delete(FieldDetectionResult).where(FieldDetectionResult.id.in_(det_ids))
            )

        ocr_ids = list(
            self.db.scalars(
                select(OCRResult.id).where(OCRResult.source_document_id == doc.id)
            ).all()
        )
        if ocr_ids:
            self.db.execute(delete(OCRPage).where(OCRPage.ocr_result_id.in_(ocr_ids)))
            self.db.execute(delete(OCRResult).where(OCRResult.id.in_(ocr_ids)))

        self.db.execute(
            delete(ProviderUsageRecord).where(
                ProviderUsageRecord.source_document_id == doc.id
            )
        )
        self.db.execute(
            delete(ProcessingJob).where(ProcessingJob.source_document_id == doc.id)
        )
        self.db.delete(doc)
        self.db.flush()

    def hard_delete_session_and_artifacts(self, session: FormSession) -> None:
        """Hard-deletes a session, its answers, export records + storage blobs,
        and its linked SourceDocument + dynamic FormVersion when unreferenced."""
        source_doc_id = session.source_document_id
        version_id = session.form_version_id

        exports = list(
            self.db.scalars(
                select(FormExport).where(FormExport.session_id == session.id)
            ).all()
        )
        for exp in exports:
            _purge_storage_blob(exp.storage_path)
            self.db.delete(exp)

        self.db.execute(delete(FormAnswer).where(FormAnswer.session_id == session.id))
        self.db.delete(session)
        self.db.flush()

        if source_doc_id:
            remaining_doc_refs = self.db.scalar(
                select(func.count())
                .select_from(FormSession)
                .where(FormSession.source_document_id == source_doc_id)
            )
            if not remaining_doc_refs:
                doc = self.db.get(SourceDocument, source_doc_id)
                if doc is not None:
                    self._purge_document_and_children(doc)

        version = self.db.get(FormVersion, version_id)
        if version is not None and version.origin == "dynamic_detection":
            remaining_version_refs = self.db.scalar(
                select(func.count())
                .select_from(FormSession)
                .where(FormSession.form_version_id == version_id)
            )
            remaining_export_refs = self.db.scalar(
                select(func.count())
                .select_from(FormExport)
                .where(FormExport.form_version_id == version_id)
            )
            if not remaining_version_refs and not remaining_export_refs:
                template_id = version.form_template_id
                self.db.delete(version)
                self.db.flush()
                sibling_versions = self.db.scalar(
                    select(func.count())
                    .select_from(FormVersion)
                    .where(FormVersion.form_template_id == template_id)
                )
                if not sibling_versions:
                    template = self.db.get(FormTemplate, template_id)
                    if template is not None:
                        self.db.delete(template)
                        self.db.flush()

    def purge_all_for_user(self, user_id: str) -> None:
        sessions = self.list_all_sessions_for_user_including_deleted(user_id)
        for session in sessions:
            self.hard_delete_session_and_artifacts(session)

        remaining_docs = self.list_owned_documents(user_id)
        for doc in remaining_docs:
            self._purge_document_and_children(doc)
        self.db.flush()
