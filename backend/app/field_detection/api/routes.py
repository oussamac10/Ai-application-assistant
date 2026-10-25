from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.ai.factory import get_ai_provider
from app.ai.mock_provider import AIProvider
from app.auth.dependencies import get_current_user_optional
from app.auth.models import User
from app.core.config import settings
from app.core.rate_limit import rate_limit_prepare
from app.database.session import get_db
from app.documents.schemas import SessionCreateRequest, SessionCreateResponse
from app.documents.service import SourceDocumentService
from app.field_detection.errors import FieldDetectionValidationError
from app.field_detection.orchestration import PrepareQuestionsService
from app.field_detection.schemas import (
    DetectedFieldSchema,
    DetectedFieldUpdateRequest,
    FieldDetectionResultResponse,
    PrepareQuestionsResponse,
    build_detected_field_schema,
    build_field_detection_response,
)
from app.field_detection.service import FieldDetectionService
from app.jobs import worker as jobs_worker
from app.jobs.schemas import PrepareQuestionsAcceptedResponse
from app.jobs.service import ProcessingJobService, serialize_prepare_result
from app.sessions.repositories import SessionRepository

router = APIRouter()

_RETRYABLE_SESSION_STATUSES = frozenset({"expired", "cancelled", "deleted"})


@router.post(
    "/source-documents/{document_id}/prepare-questions",
    response_model=PrepareQuestionsResponse | PrepareQuestionsAcceptedResponse,
    status_code=status.HTTP_200_OK,
)
async def prepare_questions(
    document_id: str,
    body: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
    current_user: User | None = Depends(get_current_user_optional),
    _rate_limit: None = Depends(rate_limit_prepare),
) -> Any:
    """Single idempotent orchestration entrypoint for the normal-user upload
    flow (Phase 13 & Phase S1-03): fast paths return 200 immediately; slow OCR /
    dynamic detection paths return 202 Accepted + `/api/jobs/{jobId}` when
    background/ARQ execution is active."""
    user_id = current_user.id if current_user else None

    if settings.JOB_EXECUTION_MODE in ("background", "arq"):
        doc = SourceDocumentService(db).get_document(
            document_id, x_document_token, user_id
        )
        existing = SessionRepository(db).get_latest_session_by_source_document_id(
            doc.id
        )
        is_fast_path = bool(doc.matched_template_key) or (
            existing is not None and existing.status not in _RETRYABLE_SESSION_STATUSES
        )
        if not is_fast_path:
            next_step = (doc.analysis_result or {}).get("next_step")
            if next_step not in ("ocr_required", "dynamic_field_detection"):
                raise FieldDetectionValidationError(
                    "This document could not be processed automatically.",
                    "cannot_process_automatically",
                )

            job_service = ProcessingJobService(db, current_user_id=user_id)
            job = job_service.create_or_reuse_prepare_job(
                doc=doc,
                user_language=body.language,
                output_language=body.outputLanguage,
            )
            if job.status == "completed" and job.result_payload is not None:
                job_status = job_service.get_job_status(job.public_id, x_document_token)
                if job_status.result is not None:
                    return job_status.result

            if job.status == "queued":
                if settings.JOB_EXECUTION_MODE == "arq":
                    await jobs_worker.enqueue_prepare_questions_job(job.public_id)
                else:
                    background_tasks.add_task(
                        jobs_worker.run_prepare_questions_job_sync, job.public_id
                    )

            accepted = PrepareQuestionsAcceptedResponse(
                documentId=doc.public_id,
                status="running" if job.status == "running" else "queued",
                jobId=job.public_id,
                pollUrl=f"/api/jobs/{job.public_id}",
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content=accepted.model_dump(),
            )

    service = PrepareQuestionsService(
        db,
        ai_provider=ai_provider,
        current_user_id=user_id,
    )
    result = await service.prepare(
        document_id, x_document_token, body.language, body.outputLanguage
    )
    return serialize_prepare_result(result)


@router.post(
    "/source-documents/{document_id}/field-detection",
    response_model=FieldDetectionResultResponse,
    status_code=status.HTTP_200_OK,
)
def request_field_detection(
    document_id: str,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = FieldDetectionService(
        db, current_user_id=current_user.id if current_user else None
    )
    result = service.request_detection(document_id, x_document_token)
    return build_field_detection_response(document_id, result)


@router.get(
    "/source-documents/{document_id}/field-detection",
    response_model=FieldDetectionResultResponse,
    status_code=status.HTTP_200_OK,
)
def get_field_detection_result(
    document_id: str,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = FieldDetectionService(
        db, current_user_id=current_user.id if current_user else None
    )
    result = service.get_detection_result(document_id, x_document_token)
    return build_field_detection_response(document_id, result)


@router.patch(
    "/source-documents/{document_id}/field-detection/fields/{field_id}",
    response_model=DetectedFieldSchema,
    status_code=status.HTTP_200_OK,
)
def update_detected_field(
    document_id: str,
    field_id: str,
    body: DetectedFieldUpdateRequest,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = FieldDetectionService(
        db, current_user_id=current_user.id if current_user else None
    )
    field = service.update_field(
        document_id,
        x_document_token,
        field_id,
        label=body.label,
        normalized_name=body.normalizedName,
        field_type=body.fieldType,
        required=body.required,
        input_bounding_box=body.inputBoundingBox.model_dump()
        if body.inputBoundingBox
        else None,
        options=body.options,
        review_status=body.reviewStatus,
    )
    return build_detected_field_schema(field)


@router.delete(
    "/source-documents/{document_id}/field-detection/fields/{field_id}",
    response_model=DetectedFieldSchema,
    status_code=status.HTTP_200_OK,
)
def reject_detected_field(
    document_id: str,
    field_id: str,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = FieldDetectionService(
        db, current_user_id=current_user.id if current_user else None
    )
    field = service.reject_field(document_id, x_document_token, field_id)
    return build_detected_field_schema(field)


@router.post(
    "/source-documents/{document_id}/field-detection/session",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_200_OK,
)
async def create_session_from_field_detection(
    document_id: str,
    body: SessionCreateRequest,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = FieldDetectionService(
        db,
        ai_provider=ai_provider,
        current_user_id=current_user.id if current_user else None,
    )
    session, session_token = await service.create_session_from_confirmed_fields(
        document_id,
        x_document_token,
        body.language,
        # The debug/review route has no detection step of its own; an
        # unspecified output language follows the interface language.
        body.outputLanguage or body.language,
    )
    return SessionCreateResponse(
        sessionId=session.public_id,
        ownershipToken=session_token,
        status="created",
    )
