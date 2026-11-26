"""add rate limit counters table

Revision ID: c8d24691a570
Revises: 1490bd5eba35
Create Date: 2026-11-26 17:34:00.000000+00:00

Rate-limit counters move out of process memory into the database so the
limits survive restarts and are shared across server instances.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d24691a570"
down_revision: str | Sequence[str] | None = "1490bd5eba35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "rate_limit_counters",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_rate_limit_counters")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("rate_limit_counters")
