"""add three state requiredness to form fields

Revision ID: cae821cb676c
Revises: 4575e921695e
Create Date: 2026-07-30 21:44:29.015571

A boolean cannot say "the document told us nothing", which is the ordinary case
for a detected field and the one that was silently resolving to *required* —
blocking users on fields the form never insisted on. The three-state column is
the source of truth; `required` stays as a derived legacy boolean.

Existing rows are backfilled from that boolean, which is the only evidence they
carry: a row that said `required = true` genuinely declared itself required
(the seeded templates set it explicitly), and `false` means optional. Newly
detected fields write `unknown` when the document carries no marker.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cae821cb676c"
down_revision: str | None = "4575e921695e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "form_fields",
        sa.Column(
            "requiredness",
            sa.String(length=10),
            server_default="unknown",
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE form_fields "
        "SET requiredness = CASE WHEN required THEN 'required' ELSE 'optional' END"
    )


def downgrade() -> None:
    # `required` is kept in sync on every write, so dropping the richer column
    # loses only the `unknown` distinction and leaves no row inconsistent.
    op.drop_column("form_fields", "requiredness")
