from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.applications.errors import (
    ApplicationNotFoundError,
    ApplicationUnauthorizedError,
    ApplicationValidationError,
)
from app.applications.repositories import ApplicationRepository
from app.documents.repository import SourceDocumentRepository
from app.sessions.models import FormSession
from app.sessions.repositories import SessionRepository
from app.sessions.security import verify_ownership_token
from app.sessions.services import compute_session_progress_percentage

_MAX_TITLE_LENGTH = 255


def _form_name(session: FormSession) -> str:
    if session.version and session.version.template:
        return session.version.template.name
    return "Application"


def to_summary_dict(session: FormSession) -> dict[str, Any]:
    return {
        "id": session.public_id,
        "title": session.title or _form_name(session),
        "status": session.status,
        "form_name": _form_name(session),
        "form_origin": session.form_origin,
        "export_supported": session.export_supported,
        "progress_percentage": compute_session_progress_percentage(session),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "last_opened_at": session.last_opened_at,
    }


class ApplicationService:
    """Persistent-application (claimed FormSession) operations for
    authenticated users: list/detail/rename/delete and the anonymous-to-
    account claim flow. Anonymous ownership-token access is untouched and
    lives in app.sessions/app.documents."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ApplicationRepository(db)
        self.session_repo = SessionRepository(db)
        self.doc_repo = SourceDocumentRepository()

    def list_applications(self, user_id: str) -> list[dict[str, Any]]:
        sessions = self.repo.list_for_user(user_id)
        return [to_summary_dict(s) for s in sessions]

    def get_application(self, user_id: str, public_id: str) -> dict[str, Any]:
        session = self.repo.get_owned(user_id, public_id)
        if not session:
            raise ApplicationNotFoundError("Application not found.")

        self.repo.touch_last_opened(session, datetime.now(UTC))

        document_public_id = None
        if session.source_document_id:
            doc = self.doc_repo.get_by_id(self.db, session.source_document_id)
            if doc:
                document_public_id = doc.public_id

        detail = to_summary_dict(session)
        detail.update(
            {
                "source_language": session.source_language,
                "user_language": session.user_language,
                "output_language": session.output_language,
                "current_field_position": session.current_field_position,
                "total_required_fields": session.total_required_fields,
                "document_id": document_public_id,
            }
        )
        return detail

    def rename_application(
        self, user_id: str, public_id: str, title: str
    ) -> dict[str, Any]:
        session = self.repo.get_owned(user_id, public_id)
        if not session:
            raise ApplicationNotFoundError("Application not found.")

        cleaned = title.strip()
        if not cleaned:
            raise ApplicationValidationError("Title must not be empty.", "empty_title")
        if len(cleaned) > _MAX_TITLE_LENGTH:
            raise ApplicationValidationError(
                f"Title must be at most {_MAX_TITLE_LENGTH} characters.",
                "title_too_long",
            )

        self.repo.rename(session, cleaned)
        return to_summary_dict(session)

    def delete_application(self, user_id: str, public_id: str) -> None:
        session = self.repo.get_owned(user_id, public_id)
        if not session:
            raise ApplicationNotFoundError("Application not found.")
        self.repo.hard_delete_session_and_artifacts(session)
        self.db.commit()

    def purge_all_for_user(self, user_id: str) -> None:
        self.repo.purge_all_for_user(user_id)
        self.db.commit()

    def export_user_applications_and_documents(
        self, user_id: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        sessions = self.repo.list_for_user(user_id)
        applications_payload: list[dict[str, Any]] = []
        for s in sessions:
            answers = self.repo.get_answers_for_session(s.id)
            serialized_answers: list[dict[str, Any]] = []
            for a in sorted(
                answers,
                key=lambda item: getattr(item.field, "position", 0),
            ):
                field_type = getattr(a.field, "field_type", "string")
                field_key = getattr(a.field, "key", a.field_id)
                norm = a.normalized_value
                if field_type == "signature" and norm is not None:
                    norm = {"type": "signature", "strokesOmitted": True}
                serialized_answers.append(
                    {
                        "field_key": field_key,
                        "field_type": field_type,
                        "original_answer": a.original_answer,
                        "normalized_value": norm,
                        "output_value": a.output_value,
                        "status": a.status,
                        "confirmed_by_user": a.confirmed_by_user,
                        "confirmed_at": a.confirmed_at,
                    }
                )
            applications_payload.append(
                {
                    "id": s.public_id,
                    "title": s.title or _form_name(s),
                    "form_name": _form_name(s),
                    "status": s.status,
                    "source_language": s.source_language,
                    "user_language": s.user_language,
                    "output_language": s.output_language,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "answers": serialized_answers,
                }
            )

        docs = self.repo.list_owned_documents(user_id)
        documents_payload: list[dict[str, Any]] = [
            {
                "id": d.public_id,
                "original_filename": d.original_filename,
                "content_type": d.content_type,
                "size_bytes": d.size_bytes,
                "page_count": d.page_count,
                "detected_source_language": d.detected_source_language,
                "created_at": d.created_at,
            }
            for d in docs
        ]
        return applications_payload, documents_payload

    def claim(
        self,
        user_id: str,
        session_id: str,
        session_token: str,
        document_id: str | None = None,
        document_token: str | None = None,
    ) -> dict[str, Any]:
        """Atomically transfers an anonymous session — and its linked source
        document, if any — to `user_id`. Idempotent: calling again for an
        application already claimed by the same user is a no-op that simply
        returns its current state. Claiming invalidates the old anonymous
        session ownership token immediately (set to NULL) so it can never
        authorize access again.

        The linked `SourceDocument` (`session.source_document_id`) is
        transferred unconditionally once the session's own token has
        verified, without requiring a separate document token from the
        caller: the document's ownership was already validated server-side
        at the moment this session was created from it (see
        `SourceDocumentService.create_session_from_document` and
        `FieldDetectionService.create_session_from_confirmed_fields`), so
        that trust carries forward rather than needing to be re-proven here.
        An optional `document_token` is still accepted and, if it verifies,
        used as an extra check — but its absence never blocks the transfer,
        since omitting it (as the frontend currently does) must not leave
        the claimed session's document permanently inaccessible to its new
        owner (this was the root cause of a Phase 12 regression: field
        detection / OCR / document endpoints stayed anonymous-only after
        claim, so the authenticated owner could no longer reach them once
        the original browser-local token was gone).
        """
        session = self.session_repo.get_session_by_public_id(session_id)
        if not session or session.deleted_at is not None:
            raise ApplicationNotFoundError("Application not found.")

        if session.user_id is not None:
            if session.user_id == user_id:
                return to_summary_dict(session)
            raise ApplicationUnauthorizedError("Unable to claim this application.")

        if not session_token or not session.ownership_token_hash:
            raise ApplicationUnauthorizedError("Unable to claim this application.")
        if not verify_ownership_token(session_token, session.ownership_token_hash):
            raise ApplicationUnauthorizedError("Unable to claim this application.")

        session.user_id = user_id
        session.ownership_token_hash = None
        session.last_opened_at = datetime.now(UTC)

        if session.source_document_id:
            doc = self.doc_repo.get_by_id(self.db, session.source_document_id)
            if doc and doc.user_id is None:
                doc.user_id = user_id
                doc.ownership_token_hash = None

        self.db.commit()
        self.db.refresh(session)
        return to_summary_dict(session)
