from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_optional
from app.auth.models import User
from app.database.session import get_db
from app.ocr.schemas import OCRRequest, OCRResultResponse, build_ocr_result_response
from app.ocr.service import OCRService

router = APIRouter()


@router.post(
    "/source-documents/{document_id}/ocr",
    response_model=OCRResultResponse,
    status_code=status.HTTP_200_OK,
)
def request_ocr(
    document_id: str,
    body: OCRRequest,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = OCRService(db, current_user_id=current_user.id if current_user else None)
    result = service.request_ocr(document_id, x_document_token, body.language)
    return build_ocr_result_response(document_id, result)


@router.get(
    "/source-documents/{document_id}/ocr",
    response_model=OCRResultResponse,
    status_code=status.HTTP_200_OK,
)
def get_ocr_result(
    document_id: str,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = OCRService(db, current_user_id=current_user.id if current_user else None)
    result = service.get_ocr_result(document_id, x_document_token)
    return build_ocr_result_response(document_id, result)
