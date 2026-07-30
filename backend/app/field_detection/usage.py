"""Per-request usage metadata for paid/remote detection providers.

Recorded so operators can see what a provider was actually asked to do —
how many pages, how long it took, whether it succeeded, and whether a
result was served from cache instead of costing another call. Deliberately
provider-agnostic (not "azure_*") so Phase 15+ providers reuse the table.

Privacy: this records *about* a request, never its content. No document
text, no extracted field labels or values, no answers, no credentials, and
no full provider payload — see docs/privacy.md.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database.session import Base


class ProviderUsageRecord(Base):
    """One row per detection-provider request attempt."""

    __tablename__ = "provider_usage_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    api_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_documents.id"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # A safe internal code (see errors.AZURE_ERROR_CODES) when the attempt
    # failed — never a provider message or stack trace.
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # The provider's own correlation id, for support tickets.
    provider_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # True when the result was reused from a prior completed run, i.e. the
    # provider was NOT called and no cost was incurred.
    served_from_cache: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Optional operator-supplied estimate; left NULL until Phase 18
    # (payments/plans) defines real pricing.
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


def record_provider_usage(
    db: Session,
    *,
    provider: str,
    source_document_id: str,
    model_id: str | None = None,
    api_version: str | None = None,
    user_id: str | None = None,
    page_count: int | None = None,
    duration_seconds: float | None = None,
    succeeded: bool = False,
    error_code: str | None = None,
    provider_request_id: str | None = None,
    served_from_cache: bool = False,
) -> ProviderUsageRecord:
    """Persists one usage row. Never raises into the caller's flow: usage
    accounting must not be able to fail a user's document processing."""
    record = ProviderUsageRecord(
        provider=provider,
        model_id=model_id,
        api_version=api_version,
        source_document_id=source_document_id,
        user_id=user_id,
        page_count=page_count,
        duration_seconds=duration_seconds,
        succeeded=succeeded,
        error_code=error_code,
        provider_request_id=provider_request_id,
        served_from_cache=served_from_cache,
        created_at=datetime.now(UTC),
    )
    db.add(record)
    db.commit()
    return record
