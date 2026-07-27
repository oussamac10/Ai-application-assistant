from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_optional
from app.auth.models import User
from app.database.session import get_db
from app.pdf.models import FormExport
from app.pdf.schemas import ExportResponse
from app.pdf.services import PDFExportService
from app.sessions.models import FormSession
from app.sessions.services import (
    ResourceNotFoundError,
    ValidationError,
)

router = APIRouter()


@router.post(
    "/form-sessions/{session_id}/exports",
    response_model=ExportResponse,
    status_code=status.HTTP_200_OK,
)
def create_pdf_export(
    session_id: str,
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> ExportResponse:
    service = PDFExportService(db)
    export = service.create_export(
        session_id, x_session_token, current_user.id if current_user else None
    )

    return ExportResponse(
        exportId=export.public_id,
        status=export.status,
        fileName=export.file_name,
        contentType=export.content_type,
        fileSize=export.file_size,
        expiresAt=export.expires_at,
        downloadUrl=f"/api/form-exports/{export.public_id}/download",
    )


@router.get(
    "/form-exports/{export_id}/download",
    response_class=FileResponse,
)
def download_pdf_export(
    export_id: str,
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> FileResponse:
    # 1. Fetch export record by public_id
    stmt = select(FormExport).where(FormExport.public_id == export_id)
    export = db.scalars(stmt).first()
    if not export:
        raise ResourceNotFoundError(f"Export with public ID '{export_id}' not found.")

    # 2. Verify Session Ownership
    session = db.get(FormSession, export.session_id)
    if not session:
        raise ResourceNotFoundError("Associated form session not found.")

    service = PDFExportService(db)
    service._verify_ownership(
        session, x_session_token, current_user.id if current_user else None
    )

    # 3. Check status constraints
    if export.status == "expired" or export.expires_at < datetime.now(UTC):
        raise ValidationError("This PDF export has expired. Please generate a new one.")
    if export.status == "failed":
        raise ValidationError("This PDF export failed to generate.")
    if export.status == "deleted":
        raise ValidationError("This PDF export file has been deleted.")
    if export.status != "completed":
        raise ValidationError(
            f"This PDF export is not ready (status: {export.status})."
        )

    # 4. Check file exists on filesystem
    filepath = Path(export.storage_path)
    if not filepath.is_file():
        raise ResourceNotFoundError("PDF file not found in temporary storage.")

    # 5. Return FileResponse streaming the file securely
    return FileResponse(
        path=str(filepath),
        filename=export.file_name,
        media_type=export.content_type,
    )
