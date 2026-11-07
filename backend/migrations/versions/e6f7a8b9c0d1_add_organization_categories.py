"""add organization categories and template category_id

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-11-07 01:25:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create organization_categories table
    op.create_table(
        "organization_categories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(length=36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "parent_id",
            sa.String(length=36),
            sa.ForeignKey("organization_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "translations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "slug", name="uq_org_categories_org_slug"
        ),
    )
    op.create_index(
        "ix_organization_categories_org_id",
        "organization_categories",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_categories_slug",
        "organization_categories",
        ["slug"],
    )
    op.create_index(
        "ix_organization_categories_parent_id",
        "organization_categories",
        ["parent_id"],
    )

    # 2. Add category_id to form_templates
    op.add_column(
        "form_templates",
        sa.Column(
            "category_id",
            sa.String(length=36),
            sa.ForeignKey("organization_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_form_templates_category_id",
        "form_templates",
        ["category_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_form_templates_category_id", table_name="form_templates")
    op.drop_column("form_templates", "category_id")

    op.drop_index(
        "ix_organization_categories_parent_id",
        table_name="organization_categories",
    )
    op.drop_index(
        "ix_organization_categories_slug",
        table_name="organization_categories",
    )
    op.drop_index(
        "ix_organization_categories_org_id",
        table_name="organization_categories",
    )
    op.drop_table("organization_categories")
