from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.ai.factory import get_ai_provider
from app.ai.mock_provider import AIProvider
from app.auth.dependencies import get_current_user_optional
from app.auth.models import User
from app.database.session import get_db
from app.documents.schemas import SessionCreateRequest, SessionCreateResponse
from app.field_detection.orchestration import PrepareQuestionsService
from app.field_detection.schemas import (
    DetectedFieldSchema,
    DetectedFieldUpdateRequest,
    FieldDetectionResultResponse,
    PrepareQuestionsResponse,
    UncertaintyInfoSchema,
    build_detected_field_schema,
    build_field_detection_response,
)
from app.field_detection.service import FieldDetectionService

router = APIRouter()


@router.post(
    "/source-documents/{document_id}/prepare-questions",
    response_model=PrepareQuestionsResponse,
    status_code=status.HTTP_200_OK,
)
async def prepare_questions(
    document_id: str,
    body: SessionCreateRequest,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    """Single idempotent orchestration entrypoint for the normal-user upload
    flow (Phase 13): analyze -> OCR (if needed) -> detect fields ->
    automatically decide what is usable -> generate questions -> create or
    reuse the guided session. Known predefined-template documents take the
    existing fast path with no OCR/detection/AI call at all."""
    service = PrepareQuestionsService(
        db,
        ai_provider=ai_provider,
        current_user_id=current_user.id if current_user else None,
    )
    result = await service.prepare(
        document_id, x_document_token, body.language, body.outputLanguage
    )
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
