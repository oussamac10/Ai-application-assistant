from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.ai.factory import get_ai_provider
from app.ai.mock_provider import AIProvider
from app.database.session import get_db
from app.documents.schemas import SessionCreateRequest, SessionCreateResponse
from app.field_detection.schemas import (
    DetectedFieldSchema,
    DetectedFieldUpdateRequest,
    FieldDetectionResultResponse,
    build_detected_field_schema,
    build_field_detection_response,
)
from app.field_detection.service import FieldDetectionService

router = APIRouter()


@router.post(
    "/source-documents/{document_id}/field-detection",
    response_model=FieldDetectionResultResponse,
    status_code=status.HTTP_200_OK,
)
def request_field_detection(
    document_id: str,
    x_document_token: str = Header(..., alias="X-Document-Token"),
    db: Session = Depends(get_db),
) -> Any:
    service = FieldDetectionService(db)
    result = service.request_detection(document_id, x_document_token)
    return build_field_detection_response(document_id, result)


@router.get(
    "/source-documents/{document_id}/field-detection",
    response_model=FieldDetectionResultResponse,
    status_code=status.HTTP_200_OK,
)
def get_field_detection_result(
    document_id: str,
    x_document_token: str = Header(..., alias="X-Document-Token"),
    db: Session = Depends(get_db),
) -> Any:
    service = FieldDetectionService(db)
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
    x_document_token: str = Header(..., alias="X-Document-Token"),
    db: Session = Depends(get_db),
) -> Any:
    service = FieldDetectionService(db)
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
    x_document_token: str = Header(..., alias="X-Document-Token"),
    db: Session = Depends(get_db),
) -> Any:
    service = FieldDetectionService(db)
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
    x_document_token: str = Header(..., alias="X-Document-Token"),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> Any:
    service = FieldDetectionService(db, ai_provider=ai_provider)
    session, session_token = await service.create_session_from_confirmed_fields(
        document_id, x_document_token, body.language, body.outputLanguage
    )
    return SessionCreateResponse(
        sessionId=session.public_id,
        ownershipToken=session_token,
        status="created",
    )
