"""add organizations and cases phase s4 b2b platform

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-01 01:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("billing_plan", sa.String(length=50), nullable=False, server_default="agency_pro"),
        sa.Column("allowed_cases_per_month", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_id", "organizations", ["id"], unique=False)
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # 2. Organization Members
    op.create_table(
        "organization_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="case_manager"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
    )
    op.create_index("ix_organization_members_id", "organization_members", ["id"], unique=False)
    op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"], unique=False)
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"], unique=False)

    # 3. Organization Cases
    op.create_table(
        "organization_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("form_version_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_name", sa.String(length=255), nullable=False),
        sa.Column("candidate_email", sa.String(length=320), nullable=False),
        sa.Column("invite_token_hash", sa.String(length=64), nullable=True),
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="invited"),
        sa.Column("form_session_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["form_version_id"], ["form_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["form_session_id"], ["form_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organization_cases_id", "organization_cases", ["id"], unique=False)
    op.create_index("ix_organization_cases_public_id", "organization_cases", ["public_id"], unique=True)
    op.create_index("ix_organization_cases_organization_id", "organization_cases", ["organization_id"], unique=False)
    op.create_index("ix_organization_cases_candidate_email", "organization_cases", ["candidate_email"], unique=False)
    op.create_index("ix_organization_cases_invite_token_hash", "organization_cases", ["invite_token_hash"], unique=True)
    op.create_index("ix_organization_cases_status", "organization_cases", ["status"], unique=False)
    op.create_index("ix_organization_cases_form_session_id", "organization_cases", ["form_session_id"], unique=False)


def downgrade() -> None:
    op.drop_table("organization_cases")
    op.drop_table("organization_members")
    op.drop_table("organizations")
