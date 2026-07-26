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
    ownership_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
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
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
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
        return bool(self.version and self.version.pdf_template_key)
