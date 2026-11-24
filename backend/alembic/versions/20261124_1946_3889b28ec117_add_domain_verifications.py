"""add domain verifications table

Revision ID: 3889b28ec117
Revises: 15e6eb52216f
Create Date: 2026-11-24 19:46:00+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3889b28ec117"
down_revision: str | Sequence[str] | None = "15e6eb52216f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "domain_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_domain_verifications")),
        sa.UniqueConstraint("domain", "owner", name=op.f("uq_domain_verifications_domain_owner")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("domain_verifications")
