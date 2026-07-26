import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.answers.models import FormAnswer
from app.core.config import settings
from app.forms.models import FormVersion
from app.pdf.formatting import format_field_value
from app.pdf.models import FormExport
from app.pdf.registry import PDFMappingError, PDFMappingLoader, PDFTemplateRegistry
from app.pdf.renderers.pypdf_renderer import PypdfRenderer
from app.pdf.validation import PDFExportValidator
from app.sessions.models import FormSession
from app.sessions.security import verify_ownership_token
from app.sessions.services import (
    ResourceNotFoundError,
    StateConflictError,
    UnauthorizedError,
    ValidationError,
)


class PDFExportService:
    def __init__(self, db: Session, fixtures_dir: Path | None = None) -> None:
        self.db = db
        self.registry = PDFTemplateRegistry(fixtures_dir)
        self.loader = PDFMappingLoader(self.registry)
        self.renderer = PypdfRenderer()
        self.validator = PDFExportValidator()

    def _verify_ownership(self, session: FormSession, token: str) -> None:
        """Verify the session ownership token using HMAC-SHA256 (matches session creation)."""
        if not verify_ownership_token(token, session.ownership_token_hash):
            raise UnauthorizedError("Invalid session credentials")

    def create_export(self, session_id: str, ownership_token: str) -> FormExport:
        # 1. Fetch FormSession by public_id (the externally-visible ID)
        session_stmt = select(FormSession).where(FormSession.public_id == session_id)
        session = self.db.scalars(session_stmt).first()
        if not session:
            raise ResourceNotFoundError(f"Session with ID '{session_id}' not found.")

        # 2. Verify Session Ownership
        self._verify_ownership(session, ownership_token)

        # 3. Check Session Expiration and Cancellation
        if session.status == "cancelled":
            raise StateConflictError("Session is cancelled.")
        if session.status == "expired" or session.expires_at < datetime.now(UTC):
            raise StateConflictError("Session has expired.")

        # 4. Check workflow state
        if session.status != "ready_for_export":
            raise StateConflictError(
                f"Session must be in 'ready_for_export' status to create export. Current: '{session.status}'"
            )

        # 5. Load Form Version and Fields
        version = self.db.get(FormVersion, session.form_version_id)
        if not version:
            raise ResourceNotFoundError("Session form version not found.")

        # Only a version with an explicit PDF template mapping can be
        # exported. Dynamically generated versions (Phase 11 confirmed-field
        # sessions) never have one — there is no reviewed coordinate mapping
        # for an arbitrary uploaded PDF, so filling/exporting it is
        # explicitly out of scope (see ADR 0010). Never guess or fall back
        # to another template's mapping.
        if not version.pdf_template_key:
            raise ValidationError(
                "This session's form is not associated with an exportable PDF template.",
                "dynamic_pdf_export_not_supported",
            )
        pdf_template_key = version.pdf_template_key

        # 6. Load explicit PDF template mapping configuration
        try:
            mapping = self.loader.load_mapping(pdf_template_key)
        except PDFMappingError as e:
            raise ValidationError(f"Failed to load PDF mapping: {str(e)}") from e

        # 7. Check if export record already exists (Idempotency)
        stmt = select(FormExport).where(
            FormExport.session_id == session.id,
            FormExport.template_key == pdf_template_key,
            FormExport.mapping_version == mapping.mapping_version,
        )
        existing_export = self.db.scalars(stmt).first()

        if existing_export:
            # If completed and file exists, return it
            if existing_export.status == "completed":
                filepath = Path(existing_export.storage_path)
                if filepath.is_file():
                    return existing_export
            # If pending or processing, wait or raise conflict
            if existing_export.status == "processing":
                raise StateConflictError("Export is already being processed.")
            # If failed, expired, deleted or file missing, we mark as processing and regenerate

        # 8. Verify all required answers are confirmed
        # Get answers for session
        stmt_answers = select(FormAnswer).where(FormAnswer.session_id == session.id)
        answers = self.db.scalars(stmt_answers).all()
        answers_by_field_id = {ans.field_id: ans for ans in answers}

        # Check required fields
        for field in version.fields:
            ans = answers_by_field_id.get(field.id)
            if field.required:
                if not ans or ans.status != "confirmed":
                    raise ValidationError(
                        f"Required field '{field.key}' is not confirmed."
                    )
            if ans:
                if ans.status == "needs_clarification":
                    raise ValidationError(
                        f"Field '{field.key}' requires clarification."
                    )
                if ans.validation_status == "invalid":
                    raise ValidationError(f"Field '{field.key}' has an invalid answer.")

        # 9. Format confirmed answers and apply overflow rules
        values_to_fill: dict[str, object] = {}
        for field_map in mapping.fields:
            # Find matching form field key
            form_field = next(
                (f for f in version.fields if f.key == field_map.field_key), None
            )
            if not form_field:
                continue

            ans = answers_by_field_id.get(form_field.id)
            if not ans:
                continue

            # Format confirmed value
            formatted_val = format_field_value(
                field_type=form_field.field_type,
                normalized_value=ans.normalized_value,
                output_value=ans.output_value,
                output_language=session.output_language,
            )

            # Check overflow rules
            if (
                field_map.max_length is not None
                and len(formatted_val) > field_map.max_length
            ):
                if field_map.overflow == "reject":
                    # Safe validation error: do NOT expose personal value contents
                    raise ValidationError(
                        f"One or more values do not fit the PDF template. (Constraint violation on field: '{field_map.field_key}')"
                    )
                elif field_map.overflow == "truncate":
                    formatted_val = formatted_val[: field_map.max_length]
                # If wrap, we keep it as is (let reader handle it)

            values_to_fill[field_map.field_key] = formatted_val

        # 10. Start rendering
        # Load registry paths
        try:
            template_path = self.registry.get_template_path(pdf_template_key)
        except PDFMappingError as e:
            raise ValidationError(str(e)) from e

        # Setup unique temp storage path
        export_dir = Path(settings.PDF_EXPORT_DIRECTORY)
        export_dir.mkdir(parents=True, exist_ok=True)
        unique_id = str(uuid.uuid4())
        filename = f"{pdf_template_key}-{unique_id}.pdf"
        output_path = export_dir / filename

        # Create or update FormExport record to 'processing'
        if existing_export:
            export = existing_export
            export.status = "processing"
            export.failed_at = None
            export.failure_code = None
        else:
            export = FormExport(
                session_id=session.id,
                form_version_id=version.id,
                template_key=pdf_template_key,
                mapping_version=mapping.mapping_version,
                status="processing",
                file_name=f"registration-{datetime.now().strftime('%Y-%m-%d')}.pdf",
                storage_path=str(output_path),
                content_type="application/pdf",
                expires_at=datetime.now(UTC)
                + timedelta(hours=settings.FORM_SESSION_TTL_HOURS),
            )
            self.db.add(export)
        self.db.commit()

        try:
            # Call PDF Renderer
            render_result = self.renderer.render(
                template_path=template_path,
                output_path=output_path,
                mapping=mapping,
                values=values_to_fill,
            )

            # Validate generated PDF and calculate checksum
            checksum = self.validator.validate(output_path)

            # Complete the export record
            export.status = "completed"
            export.file_size = render_result.file_size
            export.checksum = checksum
            export.completed_at = datetime.now(UTC)
            self.db.commit()

        except Exception as e:
            # Mark export as failed
            export.status = "failed"
            export.failed_at = datetime.now(UTC)
            export.failure_code = "GENERATION_ERROR"
            self.db.commit()
            if output_path.exists():
                try:
                    output_path.unlink()
                except OSError:
                    pass
            # Safe raise
            raise ValidationError(f"PDF rendering failed: {str(e)}") from e

        return export
