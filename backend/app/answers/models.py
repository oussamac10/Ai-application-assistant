import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class FormAnswer(Base):
    __tablename__ = "form_answers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_fields.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Nullable since Phase 15: a *skipped* optional question has no original
    # answer at all. Encoding that as an empty string would be validated,
    # normalized and counted as an invalid answer, and would be
    # indistinguishable from a question the user has not reached yet.
    original_answer: Mapped[str | None] = mapped_column(nullable=True)
    original_language: Mapped[str] = mapped_column(String(10), nullable=False)
    normalized_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    output_value: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="unanswered", nullable=False, index=True
    )
    validation_status: Mapped[str] = mapped_column(
        String(50), default="not_checked", nullable=False, index=True
    )
    translation_status: Mapped[str] = mapped_column(
        String(50), default="not_required", nullable=False
    )
    requires_clarification: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    confirmed_by_user: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("session_id", "field_id", name="uq_session_field_answer"),
    )

    session = relationship("FormSession", back_populates="answers")
    field = relationship("FormField")
