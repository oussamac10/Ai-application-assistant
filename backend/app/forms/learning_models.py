"""Zero-PII continual schema learning models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class LearnedFormPattern(Base):
    """Stores structural field, choice-group, and table-row curations without PII.

    Populated strictly from template/studio labels, option values, table column
    headers, and Vault key mappings — never from applicant answers or case data.
    """

    __tablename__ = "learned_form_patterns"
    __table_args__ = (
        Index(
            "ix_learned_form_patterns_lookup",
            "pattern_type",
            "signature_hash",
        ),
        Index(
            "ix_learned_form_patterns_org_scope",
            "source_organization_id",
            "scope",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    source_organization_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="organization",
        server_default="organization",
        index=True,
    )
    pattern_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    signature_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    source_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="de",
        server_default="de",
        index=True,
    )
    normalized_signature: Mapped[str] = mapped_column(Text, nullable=False)
    raw_header_tokens: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    canonical_field_type: Mapped[str] = mapped_column(String(40), nullable=False)
    canonical_question_key: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
    )
    canonical_requiredness: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    canonical_options_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    table_structure_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    translations_json: Mapped[dict[str, dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    embedding_json: Mapped[list[float] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    confirmation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    last_confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
