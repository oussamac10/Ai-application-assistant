import hashlib
import os
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.documents.analyzer import PDFAnalyzer
from app.documents.errors import (
    DocumentNotFoundError,
    DocumentStateConflictError,
    DocumentUnauthorizedError,
    DocumentValidationError,
)
from app.documents.image_normalizer import (
    detect_upload_media_kind,
    is_candidate_upload_type,
    normalize_image_file_to_a4_pdf,
)
from app.documents.models import SourceDocument
from app.documents.registry import PDFFingerprintRegistry
from app.documents.repository import SourceDocumentRepository
from app.documents.storage import DocumentStorage, sanitize_filename
from app.documents.validation import (
    validate_pdf_safety,
    validate_pdf_signature,
    validate_pdf_structure,
)
from app.forms.models import FormTemplate, FormVersion
from app.sessions.security import (
    generate_ownership_token,
    hash_ownership_token,
    verify_ownership_token,
)
from app.sessions.services import SessionService


class SourceDocumentService:
    def __init__(self, db: Session, *, trusted_worker: bool = False):
        self.db = db
        self.repo = SourceDocumentRepository()
        self.storage = DocumentStorage()
        self.analyzer = PDFAnalyzer()
        self.registry = PDFFingerprintRegistry()
        self._trusted_worker = trusted_worker

    def upload_and_analyze(
        self,
        filename: str,
        content_type: str,
        file_chunks: Iterable[bytes],
        privacy_accepted: bool,
        user_language: str,
        output_language: str,
        current_user_id: str | None = None,
    ) -> tuple[SourceDocument, str]:
        """Handles streaming upload, validation, analysis, and fingerprint matching of a PDF document."""
        if not privacy_accepted:
            raise DocumentValidationError(
                "Privacy policy must be accepted.", "privacy_not_accepted"
            )

        if not is_candidate_upload_type(filename, content_type):
            raise DocumentValidationError(
                "Only PDF, JPG, PNG, and WebP files are supported.",
                "invalid_file_type",
            )

        # 1. Stream file to private storage and compute checksum/size
        target_path = self.storage.generate_storage_path()
        sha256 = hashlib.sha256()
        bytes_written = 0

        try:
            with open(target_path, "wb") as f:
                for chunk in file_chunks:
                    bytes_written += len(chunk)
                    if bytes_written > settings.DOCUMENT_UPLOAD_MAX_BYTES:
                        raise DocumentValidationError(
                            f"File size exceeds limit of {settings.DOCUMENT_UPLOAD_MAX_BYTES} bytes.",
                            "file_too_large",
                        )
                    sha256.update(chunk)
                    f.write(chunk)
        except Exception as e:
            # Clean up partial upload
            if target_path.is_file():
                os.unlink(target_path)
            if isinstance(e, DocumentValidationError):
                raise
            raise DocumentValidationError(
                f"File upload failed: {str(e)}", "malformed_pdf"
            ) from e

        if bytes_written == 0:
            if target_path.is_file():
                os.unlink(target_path)
            raise DocumentValidationError("Uploaded file is empty.", "malformed_pdf")

        # 2. Verify real magic bytes and normalize camera images (EXIF transpose
        # + GPS/EXIF strip + A4 PDF page) or sanitize PDF active scripts.
        try:
            source_media_type = detect_upload_media_kind(str(target_path))
            if source_media_type == "application/pdf":
                validate_pdf_signature(str(target_path))
                validate_pdf_structure(
                    str(target_path), settings.DOCUMENT_UPLOAD_MAX_PAGES
                )
                validate_pdf_safety(str(target_path))
            else:
                normalize_image_file_to_a4_pdf(
                    str(target_path),
                    settings.DOCUMENT_UPLOAD_MAX_IMAGE_PIXELS,
                    source_media_type,
                )
                sha256 = hashlib.sha256(target_path.read_bytes())
            bytes_written = target_path.stat().st_size
        except Exception:
            # Clean up invalid file
            if target_path.is_file():
                os.unlink(target_path)
            raise

        # 3. Analyze PDF structure
        try:
            analysis = self.analyzer.analyze_document(str(target_path))
        except Exception as e:
            if target_path.is_file():
                os.unlink(target_path)
            raise DocumentValidationError(
                f"PDF structural analysis failed: {str(e)}", "document_analysis_failed"
            ) from e

        # 4. Fingerprint pre-defined template recognition
        matched_template = self.registry.match_document(str(target_path), analysis)
        matched_template_key = None
        matched_form_key = None
        matched_form_version = None

        if matched_template:
            matched_template_key = matched_template.get("templateKey")
            matched_form_key = matched_template.get("formKey")
            matched_form_version = matched_template.get("formVersion")
            analysis["matched_template"] = {
                "templateKey": matched_template_key,
                "formKey": matched_form_key,
                "formVersion": matched_form_version,
            }
        else:
            analysis["matched_template"] = None

        # 5. Resolve next step
        # matched predefined template -> supported_template
        # scanned PDF -> ocr_required
        # digital / fillable / hybrid PDF with native text or AcroForm -> dynamic_field_detection
        # image-bearing PDF without native text -> ocr_required
        # empty / unknown PDF -> review_required
        if matched_template:
            next_step = "supported_template"
        elif analysis.get("is_probably_scanned", False):
            next_step = "ocr_required"
        elif (
            analysis.get("document_type") in ("digital_pdf", "fillable_pdf")
            or analysis.get("has_native_text", False)
            or analysis.get("has_acroform", False)
        ):
            next_step = "dynamic_field_detection"
        elif analysis.get("has_embedded_images", False):
            next_step = "ocr_required"
        else:
            next_step = "review_required"

        analysis["next_step"] = next_step
        analysis["source_media_type"] = source_media_type

        # 6. Persist validated & sanitized PDF via StorageProvider (Local or EU S3)
        try:
            storage_ref = self.storage.persist_uploaded_file(target_path)
        except Exception as e:
            if target_path.is_file():
                os.unlink(target_path)
            raise DocumentValidationError(
                "Document storage failed.", "document_storage_failed"
            ) from e

        # 7. Generate ownership token and hash it
        raw_token = generate_ownership_token()
        token_hash = hash_ownership_token(raw_token)

        # 8. Create SourceDocument entity
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=settings.DOCUMENT_EXPIRATION_HOURS)

        doc = SourceDocument(
            ownership_token_hash=token_hash,
            user_id=current_user_id,
            original_filename=filename,
            sanitized_filename=sanitize_filename(filename),
            storage_path=storage_ref,
            content_type="application/pdf",
            size_bytes=bytes_written,
            checksum_sha256=sha256.hexdigest(),
            status="analyzed",
            page_count=analysis.get("page_count", 0),
            document_type=analysis.get("document_type", "unknown_pdf"),
            has_native_text=analysis.get("has_native_text", False),
            has_acroform=analysis.get("has_acroform", False),
            has_embedded_images=analysis.get("has_embedded_images", False),
            is_probably_scanned=analysis.get("is_probably_scanned", False),
            matched_template_key=matched_template_key,
            matched_form_key=matched_form_key,
            matched_form_version=matched_form_version,
            analysis_version=settings.DOCUMENT_ANALYSIS_VERSION,
            analysis_result=analysis,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )

        self.repo.create(self.db, doc)
        return doc, raw_token

    def get_document(
        self,
        public_id: str,
        ownership_token: str | None,
        current_user_id: str | None = None,
    ) -> SourceDocument:
        """Retrieves document if ownership token matches and document is not
        expired. Mirrors SessionService.get_session's dual-ownership model:
        once a document has an owning user, only that user can access it;
        the anonymous token is never consulted for it again."""
        doc = self.repo.get_by_public_id(self.db, public_id)
        if not doc:
            raise DocumentNotFoundError("Document not found.")

        if doc.status in ("deleted", "expired"):
            raise DocumentNotFoundError("Document has expired or been deleted.")

        if not self._trusted_worker:
            if doc.user_id is not None:
                if not current_user_id or current_user_id != doc.user_id:
                    raise DocumentUnauthorizedError("Invalid document credentials.")
            else:
                if not ownership_token or not doc.ownership_token_hash:
                    raise DocumentUnauthorizedError("Invalid document credentials.")
                if not verify_ownership_token(
                    ownership_token, doc.ownership_token_hash
                ):
                    raise DocumentUnauthorizedError("Invalid document credentials.")

        # Verify expiration — an authenticated (claimed) document is not
        # time-boxed by its original anonymous expiration window.
        if doc.user_id is None and datetime.now(UTC) >= doc.expires_at:
            doc.status = "expired"
            self.repo.update(self.db, doc)
            raise DocumentNotFoundError("Document has expired.")

        return doc

    def create_session_from_document(
        self,
        public_id: str,
        ownership_token: str | None,
        user_lang: str,
        output_lang: str,
        current_user_id: str | None = None,
    ) -> tuple[Any, str]:
        """Creates a form session using the matched predefined template details."""
        doc = self.get_document(public_id, ownership_token, current_user_id)

        if doc.status != "analyzed":
            raise DocumentStateConflictError("Document is not in analyzed state.")

        if (
            not doc.matched_template_key
            or not doc.matched_form_key
            or not doc.matched_form_version
        ):
            raise DocumentStateConflictError(
                "No supported predefined template matched for this document."
            )

        # Find the published FormVersion linked to the matched form template and version number
        stmt = (
            select(FormVersion)
            .join(FormTemplate)
            .where(FormTemplate.key == doc.matched_form_key)
            .where(FormVersion.version_number == doc.matched_form_version)
            .where(FormVersion.status == "published")
        )
        form_version = self.db.scalars(stmt).first()
        if not form_version:
            raise DocumentStateConflictError(
                f"Form template version '{doc.matched_form_key}' v{doc.matched_form_version} is not published."
            )

        # Call existing SessionService to instantiate session
        session_service = SessionService(self.db)
        session, session_token = session_service.create_session(
            form_version_id=form_version.id,
            user_language=user_lang,
            output_language=output_lang,
            current_user_id=current_user_id,
            source_document_id=doc.id,
        )

        return session, session_token
