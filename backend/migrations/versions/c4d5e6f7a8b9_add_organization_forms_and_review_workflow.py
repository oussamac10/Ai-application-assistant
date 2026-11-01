"""add organization forms and review workflow columns

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-11-01 16:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add organization ownership and metadata to form_templates
    op.add_column(
        "form_templates",
        sa.Column(
            "organization_id",
            sa.String(length=36),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_form_templates_organization_id",
        "form_templates",
        ["organization_id"],
        unique=False,
    )
    op.add_column(
        "form_templates",
        sa.Column(
            "category",
            sa.String(length=100),
            nullable=False,
            server_default="general",
        ),
    )
    op.create_index(
        "ix_form_templates_category",
        "form_templates",
        ["category"],
        unique=False,
    )
    op.add_column(
        "form_templates",
        sa.Column(
            "submission_method",
            sa.String(length=50),
            nullable=False,
            server_default="print_and_sign",
        ),
    )
    op.add_column(
        "form_templates",
        sa.Column(
            "instructions",
            sa.Text(),
            nullable=True,
        ),
    )
    op.add_column(
        "form_templates",
        sa.Column(
            "required_documents",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # 2. Add source PDF path and review notes to form_versions
    op.add_column(
        "form_versions",
        sa.Column(
            "source_pdf_storage_path",
            sa.String(length=500),
            nullable=True,
        ),
    )
    op.add_column(
        "form_versions",
        sa.Column(
            "review_notes",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("form_versions", "review_notes")
    op.drop_column("form_versions", "source_pdf_storage_path")

    op.drop_column("form_templates", "required_documents")
    op.drop_column("form_templates", "instructions")
    op.drop_column("form_templates", "submission_method")
    op.drop_index("ix_form_templates_category", table_name="form_templates")
    op.drop_column("form_templates", "category")
    op.drop_index("ix_form_templates_organization_id", table_name="form_templates")
    op.drop_column("form_templates", "organization_id")
