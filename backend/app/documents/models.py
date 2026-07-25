import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SourceDocument(Base):
    __tablename__ = "source_documents"

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
    ownership_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sanitized_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
        index=True,
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    document_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    has_native_text: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    has_acroform: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    has_embedded_images: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    is_probably_scanned: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    matched_template_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    matched_form_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    matched_form_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    analysis_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    analysis_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
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
