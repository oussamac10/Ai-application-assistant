"""add learned_form_patterns table for zero-pii schema learning

Revision ID: i0d1e2f3a4b5
Revises: h9c0d1e2f3a4
Create Date: 2026-11-15 16:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i0d1e2f3a4b5"
down_revision: str | None = "h9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learned_form_patterns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_organization_id", sa.String(length=36), nullable=True),
        sa.Column(
            "scope",
            sa.String(length=20),
            server_default="organization",
            nullable=False,
        ),
        sa.Column("pattern_type", sa.String(length=32), nullable=False),
        sa.Column("signature_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "source_language",
            sa.String(length=10),
            server_default="de",
            nullable=False,
        ),
        sa.Column("normalized_signature", sa.Text(), nullable=False),
        sa.Column(
            "raw_header_tokens",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("canonical_field_type", sa.String(length=40), nullable=False),
        sa.Column("canonical_question_key", sa.String(length=120), nullable=True),
        sa.Column(
            "canonical_requiredness",
            sa.String(length=20),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column(
            "canonical_options_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "table_structure_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "translations_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "embedding_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "confirmation_count",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "last_confirmed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_organization_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_learned_form_patterns_lookup",
        "learned_form_patterns",
        ["pattern_type", "signature_hash"],
        unique=False,
    )
    op.create_index(
        "ix_learned_form_patterns_org_scope",
        "learned_form_patterns",
        ["source_organization_id", "scope"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learned_form_patterns_source_organization_id"),
        "learned_form_patterns",
        ["source_organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learned_form_patterns_scope"),
        "learned_form_patterns",
        ["scope"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learned_form_patterns_pattern_type"),
        "learned_form_patterns",
        ["pattern_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learned_form_patterns_signature_hash"),
        "learned_form_patterns",
        ["signature_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learned_form_patterns_source_language"),
        "learned_form_patterns",
        ["source_language"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learned_form_patterns_canonical_question_key"),
        "learned_form_patterns",
        ["canonical_question_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_learned_form_patterns_canonical_question_key"),
        table_name="learned_form_patterns",
    )
    op.drop_index(
        op.f("ix_learned_form_patterns_source_language"),
        table_name="learned_form_patterns",
    )
    op.drop_index(
        op.f("ix_learned_form_patterns_signature_hash"),
        table_name="learned_form_patterns",
    )
    op.drop_index(
        op.f("ix_learned_form_patterns_pattern_type"),
        table_name="learned_form_patterns",
    )
    op.drop_index(
        op.f("ix_learned_form_patterns_scope"),
        table_name="learned_form_patterns",
    )
    op.drop_index(
        op.f("ix_learned_form_patterns_source_organization_id"),
        table_name="learned_form_patterns",
    )
    op.drop_index(
        "ix_learned_form_patterns_org_scope",
        table_name="learned_form_patterns",
    )
    op.drop_index(
        "ix_learned_form_patterns_lookup",
        table_name="learned_form_patterns",
    )
    op.drop_table("learned_form_patterns")
