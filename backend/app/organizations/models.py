import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.auth.models import User


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    billing_plan: Mapped[str] = mapped_column(
        String(50), default="agency_pro", nullable=False
    )
    allowed_cases_per_month: Mapped[int] = mapped_column(
        Integer, default=50, nullable=False
    )

    # Type: "government" (Authority, City, University, Consulate) vs "business" (Relocation agency, Law firm)
    organization_type: Mapped[str] = mapped_column(
        String(50), default="government", server_default="government", nullable=False
    )

    # Government / Official Status & Verification
    verification_status: Mapped[str] = mapped_column(
        String(30), default="unverified", nullable=False
    )  # unverified, pending_review, verified_official, rejected
    is_verified_government: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    verification_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    # Profile & Public Branding
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_image_storage_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    office_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    official_website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    supported_languages: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["de", "en"], nullable=False
    )
    ui_theme_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    cases: Mapped[list["OrganizationCase"]] = relationship(
        "OrganizationCase", back_populates="organization", cascade="all, delete-orphan"
    )
    categories: Mapped[list["OrganizationCategory"]] = relationship(
        "OrganizationCategory",
        back_populates="organization",
        cascade="all, delete-orphan",
        order_by="OrganizationCategory.sort_order.asc()",
    )


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(30), default="case_manager", nullable=False
    )  # owner, admin, form_editor, viewer, case_manager
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="members"
    )
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", name="uq_organization_members_org_user"
        ),
    )


class OrganizationCase(Base):
    __tablename__ = "organization_cases"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    form_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_email: Mapped[str] = mapped_column(
        String(320), nullable=False, index=True
    )
    invite_token_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    invite_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="invited", nullable=False, index=True
    )  # invited, in_progress, awaiting_review, completed
    form_session_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("form_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="cases"
    )


class OrganizationCategory(Base):
    __tablename__ = "organization_categories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organization_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    translations: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="categories"
    )
    parent: Mapped[Any | None] = relationship(
        "OrganizationCategory", remote_side=[id], backref="children"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_org_categories_org_slug"),
    )
