"""add journey steps, previous run and domain verification to audit runs

Revision ID: 866885181374
Revises: f90222b04564
Create Date: 2026-11-24 01:40:00+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "866885181374"
down_revision: str | Sequence[str] | None = "f90222b04564"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Batch mode: SQLite cannot add a foreign key to an existing table
    # without rebuilding it, and Alembic only does that in batch mode.
    with op.batch_alter_table("audit_runs") as batch_op:
        batch_op.add_column(sa.Column("journey_steps", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("previous_run_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "domain_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.create_foreign_key(
            op.f("fk_audit_runs_previous_run_id_audit_runs"),
            "audit_runs",
            ["previous_run_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("audit_runs") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_audit_runs_previous_run_id_audit_runs"), type_="foreignkey"
        )
        batch_op.drop_column("domain_verified")
        batch_op.drop_column("previous_run_id")
        batch_op.drop_column("journey_steps")
