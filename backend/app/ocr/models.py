import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
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


class OCRResult(Base):
    """One OCR run per source document. Idempotent: re-requesting OCR for the
    same document returns/updates this row rather than creating a new one.
    """

    __tablename__ = "ocr_results"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id", name="uq_ocr_results_source_document_id"
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
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )
    provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    pages: Mapped[list["OCRPage"]] = relationship(
        "OCRPage",
        back_populates="ocr_result",
        cascade="all, delete-orphan",
        order_by="OCRPage.page_number",
    )


class OCRPage(Base):
    """Normalized page-level OCR output. Coordinates are in rendered-image
    pixel space (see ADR 0009), not PDF point space. Text/geometry only —
    never field-semantic data.
    """

    __tablename__ = "ocr_pages"
    __table_args__ = (
        UniqueConstraint(
            "ocr_result_id", "page_number", name="uq_ocr_pages_result_page"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    ocr_result_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ocr_results.id"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    average_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    lines: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ocr_result: Mapped["OCRResult"] = relationship("OCRResult", back_populates="pages")
