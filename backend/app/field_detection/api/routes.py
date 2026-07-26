from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.field_detection.schemas import (
    FieldDetectionResultResponse,
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
