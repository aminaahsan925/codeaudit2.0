"""merge journey definition and finding tracking heads

Revision ID: 15e6eb52216f
Revises: aac61ff04c99, 6dea55f8ec53
Create Date: 2026-11-24 11:14:07.132631+00:00

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "15e6eb52216f"
down_revision: str | Sequence[str] | None = ("aac61ff04c99", "6dea55f8ec53")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
