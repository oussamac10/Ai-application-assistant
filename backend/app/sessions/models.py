import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.forms.models import FormVersion


class FormSession(Base):
    __tablename__ = "form_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    # Nullable: cleared (set to NULL) the moment a session is claimed by an
    # authenticated user (see app/applications/services.py claim flow) so
    # the old anonymous token can never authorize access again. Exactly one
    # of (ownership_token_hash present) / (user_id present) is meaningful
    # at a time — never both.
    ownership_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Convenience link for resume/rename/delete/title-generation — not all
    # sessions originate from an uploaded document (predefined-template
    # sessions created via "Select Manually" have none).
    source_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    form_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_language: Mapped[str] = mapped_column(String(10), nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    output_language: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="session_created", nullable=False
    )
    current_field_position: Mapped[int] = mapped_column(default=0, nullable=False)
    total_required_fields: Mapped[int] = mapped_column(default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "current_field_position >= 0",
            name="ck_session_current_field_position",
        ),
        CheckConstraint(
            "total_required_fields >= 0", name="ck_session_total_required_fields"
        ),
    )

    version: Mapped["FormVersion"] = relationship("FormVersion")

    @property
    def form_origin(self) -> str:
        return self.version.origin if self.version else "predefined_template"

    @property
    def export_supported(self) -> bool:
        return bool(
            (self.version and self.version.pdf_template_key) or self.source_document_id
        )
