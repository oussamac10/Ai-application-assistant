from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.ai.factory import get_ai_provider
from app.core.config import settings
from app.documents.errors import DocumentNotFoundError
from app.documents.models import SourceDocument
from app.documents.service import SourceDocumentService
from app.field_detection.orchestration import (
    PrepareQuestionsResult,
    PrepareQuestionsService,
)
from app.field_detection.schemas import (
    PrepareQuestionsResponse,
    UncertaintyInfoSchema,
)
from app.jobs.crypto import decrypt_job_token, encrypt_job_token
from app.jobs.models import ProcessingJob
from app.jobs.repository import ProcessingJobRepository
from app.jobs.schemas import JobStatusResponse


def serialize_prepare_result(
    result: PrepareQuestionsResult,
) -> PrepareQuestionsResponse:
    return PrepareQuestionsResponse(
        documentId=result.document_public_id,
        status=result.status,
        sessionId=result.session.public_id if result.session else None,
        ownershipToken=result.ownership_token,
        reusedExistingSession=result.reused_existing_session,
        uncertainty=(
            UncertaintyInfoSchema(
                hasUncertainFields=result.uncertainty.has_uncertain_fields,
                uncertainFieldCount=result.uncertainty.uncertain_field_count,
            )
            if result.uncertainty
            else None
        ),
        errorCode=result.error_code,
        stage=result.stage,
    )


class ProcessingJobService:
    def __init__(self, db: Session, *, current_user_id: str | None = None):
        self.db = db
        self.repo = ProcessingJobRepository()
        self.document_service = SourceDocumentService(db)
        self.current_user_id = current_user_id

    def create_or_reuse_prepare_job(
        self,
        *,
        doc: SourceDocument,
        user_language: str,
        output_language: str | None,
    ) -> ProcessingJob:
        idem_key = f"prepare:{doc.id}:{user_language}:{output_language or 'auto'}"
        existing = self.repo.get_active_or_completed_by_idempotency_key(
            self.db, idem_key
        )
        now = datetime.now(UTC)
        if existing is not None and existing.expires_at > now:
            return existing

        job = ProcessingJob(
            source_document_id=doc.id,
            user_id=self.current_user_id,
            job_type="prepare_questions",
            idempotency_key=idem_key,
            status="queued",
            stage="queued",
            payload={
                "document_public_id": doc.public_id,
                "user_language": user_language,
                "output_language": output_language,
            },
            expires_at=now + timedelta(hours=settings.JOB_EXPIRATION_HOURS),
            created_at=now,
            updated_at=now,
        )
        return self.repo.create(self.db, job)

    def get_job_status(
        self,
        job_public_id: str,
        ownership_token: str | None,
    ) -> JobStatusResponse:
        job = self.repo.get_by_public_id(self.db, job_public_id)
        if job is None:
            raise DocumentNotFoundError("Processing job not found.")

        payload = job.payload or {}
        doc_public_id = str(payload.get("document_public_id") or "")
        # Strict ownership check: enforces either authenticated owner or valid X-Document-Token
        doc = self.document_service.get_document(
            doc_public_id, ownership_token, self.current_user_id
        )
        if doc.id != job.source_document_id:
            raise DocumentNotFoundError("Processing job not found.")

        result_schema: PrepareQuestionsResponse | None = None
        if job.result_payload is not None:
            hydrated = dict(job.result_payload)
            decrypted_token = decrypt_job_token(job.encrypted_session_token)
            if decrypted_token:
                hydrated["ownershipToken"] = decrypted_token
            result_schema = PrepareQuestionsResponse.model_validate(hydrated)

        return JobStatusResponse(
            jobId=job.public_id,
            documentId=doc.public_id,
            jobType=job.job_type,
            status=job.status,  # type: ignore[arg-type]
            stage=job.stage,
            result=result_schema,
            errorCode=job.error_code,
        )

    async def execute_prepare_job_by_public_id(self, job_public_id: str) -> None:
        job = self.repo.get_by_public_id(self.db, job_public_id)
        if job is None or job.status == "completed":
            return

        now = datetime.now(UTC)
        job.status = "running"
        job.stage = "processing"
        job.started_at = now
        self.repo.update(self.db, job)

        payload = job.payload or {}
        doc_public_id = str(payload.get("document_public_id") or "")
        user_language = str(payload.get("user_language") or "en")
        output_language = payload.get("output_language")

        try:
            ai_provider = get_ai_provider()
            orchestrator = PrepareQuestionsService(
                self.db,
                ai_provider=ai_provider,
                current_user_id=job.user_id,
                trusted_worker=True,
            )
            result = await orchestrator.prepare(
                doc_public_id,
                None,
                user_language,
                output_language,
            )
            response_obj = serialize_prepare_result(result)
            # Strip raw session ownershipToken before writing JSON to DB; encrypt separately!
            sanitized_dict = response_obj.model_dump()
            raw_session_token = sanitized_dict.pop("ownershipToken", None)
            sanitized_dict["ownershipToken"] = None

            job.result_payload = sanitized_dict
            job.encrypted_session_token = encrypt_job_token(raw_session_token)
            job.completed_at = datetime.now(UTC)
            if result.status == "failed":
                job.status = "failed"
                job.stage = result.stage
                job.error_code = result.error_code or "document_processing_failed"
            else:
                job.status = "completed"
                job.stage = None
                job.error_code = None
            self.repo.update(self.db, job)
        except Exception:
            job.status = "failed"
            job.stage = "orchestration"
            job.error_code = "document_processing_failed"
            job.completed_at = datetime.now(UTC)
            self.repo.update(self.db, job)
