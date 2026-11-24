"""add finding assignment tracking

Revision ID: aac61ff04c99
Revises: 1490bd5eba35
Create Date: 2026-11-24 10:53:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aac61ff04c99"
down_revision: str | Sequence[str] | None = "1490bd5eba35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("findings", sa.Column("assignee", sa.String(length=200), nullable=True))
    # server_default backfills existing rows as "open" and stays: it matches
    # the model default, and SQLite cannot drop a column default afterwards.
    op.add_column(
        "findings",
        sa.Column(
            "tracking_status",
            sa.String(length=20),
            server_default="open",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("findings", "tracking_status")
    op.drop_column("findings", "assignee")
