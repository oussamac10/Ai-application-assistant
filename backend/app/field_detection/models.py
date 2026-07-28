import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class FieldDetectionResult(Base):
    """One active detection run per document + analysis version. A new
    analysis_version (e.g. after a provider/heuristics upgrade) is allowed to
    create a new result row rather than overwriting the prior one.
    """

    __tablename__ = "field_detection_results"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "analysis_version",
            name="uq_field_detection_results_document_version",
        ),
    )

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
    source_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("source_documents.id"),
        nullable=False,
        index=True,
    )
    ocr_result_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ocr_results.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )
    provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    field_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Phase 13: safe counters only (auto-confirmed/medium/needs-clarification/
    # rejected/total field counts) for later Phase 14 admin review — never
    # populated with field labels, values, or document text. See
    # app/field_detection/question_bridge.py:build_review_metadata.
    review_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    fields: Mapped[list["DetectedField"]] = relationship(
        "DetectedField",
        back_populates="detection_result",
        cascade="all, delete-orphan",
        order_by="DetectedField.display_order",
    )


class DetectedField(Base):
    """A single reviewable candidate field. Coordinates are in the source's
    native space: PDF point space for native/acroform candidates, rendered-
    image pixel space (see ADR 0009) for ocr candidates — `source` records
    which."""

    __tablename__ = "detected_fields"
    __table_args__ = (
        UniqueConstraint(
            "detection_result_id",
            "display_order",
            name="uq_detected_fields_result_order",
        ),
    )

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
    detection_result_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("field_detection_results.id"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(String(50), nullable=False)
    required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    multiple: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    label_bounding_box: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    input_bounding_box: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    existing_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(50),
        default="pending_review",
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    detection_result: Mapped["FieldDetectionResult"] = relationship(
        "FieldDetectionResult", back_populates="fields"
    )
    options: Mapped[list["DetectedFieldOption"]] = relationship(
        "DetectedFieldOption",
        back_populates="detected_field",
        cascade="all, delete-orphan",
        order_by="DetectedFieldOption.position",
    )


class DetectedFieldOption(Base):
    """A single choice option for a radio/select DetectedField candidate."""

    __tablename__ = "detected_field_options"
    __table_args__ = (
        UniqueConstraint(
            "detected_field_id", "position", name="uq_detected_field_options_position"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    detected_field_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("detected_fields.id"),
        nullable=False,
        index=True,
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    detected_field: Mapped["DetectedField"] = relationship(
        "DetectedField", back_populates="options"
    )
