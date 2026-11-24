"""add journey definition to audit runs

Revision ID: 6dea55f8ec53
Revises: 1490bd5eba35
Create Date: 2026-11-24 16:00:00+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6dea55f8ec53"
down_revision: str | Sequence[str] | None = "1490bd5eba35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("audit_runs") as batch_op:
        batch_op.add_column(sa.Column("journey_definition", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("audit_runs") as batch_op:
        batch_op.drop_column("journey_definition")
