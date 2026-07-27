from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_optional
from app.auth.models import User
from app.database.session import get_db
from app.documents.schemas import (
    DocumentAnalysisSummary,
    DocumentRetrieveResponse,
    DocumentUploadResponse,
    SessionCreateRequest,
    SessionCreateResponse,
)
from app.documents.service import SourceDocumentService

router = APIRouter()


def chunk_generator(
    upload_file: UploadFile, chunk_size: int = 65536
) -> Iterator[bytes]:
    """Synchronously yields chunks of the uploaded file's content."""
    upload_file.file.seek(0)
    while True:
        chunk = upload_file.file.read(chunk_size)
        if not chunk:
            break
        yield chunk


@router.post(
    "/source-documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    language: str = Form(...),
    outputLanguage: str = Form(...),
    privacyAccepted: bool = Form(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = SourceDocumentService(db)

    # Convert chunk_generator to an iterable
    file_chunks = chunk_generator(file)

    doc, raw_token = service.upload_and_analyze(
        filename=file.filename or "document.pdf",
        content_type=file.content_type or "application/pdf",
        file_chunks=file_chunks,
        privacy_accepted=privacyAccepted,
        user_language=language,
        output_language=outputLanguage,
        current_user_id=current_user.id if current_user else None,
    )

    # Format the analysis response
    ar = doc.analysis_result or {}
    analysis_summary = DocumentAnalysisSummary(
        pageCount=doc.page_count or 0,
        documentType=doc.document_type or "unknown_pdf",
        hasNativeText=doc.has_native_text or False,
        hasAcroForm=doc.has_acroform or False,
        hasEmbeddedImages=doc.has_embedded_images or False,
        isProbablyScanned=doc.is_probably_scanned or False,
        matchedTemplate=ar.get("matched_template"),
        nextStep=ar.get("next_step", "review_required"),
    )

    return DocumentUploadResponse(
        documentId=doc.public_id,
        ownershipToken=raw_token,
        status=doc.status,
        analysis=analysis_summary,
        expiresAt=doc.expires_at,
    )


@router.get(
    "/source-documents/{document_id}",
    response_model=DocumentRetrieveResponse,
    status_code=status.HTTP_200_OK,
)
def get_document(
    document_id: str,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = SourceDocumentService(db)
    doc = service.get_document(
        document_id, x_document_token, current_user.id if current_user else None
    )

    ar = doc.analysis_result or {}
    analysis_summary = DocumentAnalysisSummary(
        pageCount=doc.page_count or 0,
        documentType=doc.document_type or "unknown_pdf",
        hasNativeText=doc.has_native_text or False,
        hasAcroForm=doc.has_acroform or False,
        hasEmbeddedImages=doc.has_embedded_images or False,
        isProbablyScanned=doc.is_probably_scanned or False,
        matchedTemplate=ar.get("matched_template"),
        nextStep=ar.get("next_step", "review_required"),
    )

    return DocumentRetrieveResponse(
        documentId=doc.public_id,
        status=doc.status,
        analysis=analysis_summary,
        expiresAt=doc.expires_at,
    )


@router.post(
    "/source-documents/{document_id}/session",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_200_OK,
)
def create_session(
    document_id: str,
    body: SessionCreateRequest,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = SourceDocumentService(db)
    session, session_token = service.create_session_from_document(
        document_id,
        x_document_token,
        body.language,
        body.outputLanguage,
        current_user_id=current_user.id if current_user else None,
    )

    return SessionCreateResponse(
        sessionId=session.public_id,
        ownershipToken=session_token,
        status="created",
    )
