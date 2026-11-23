"""SQLAlchemy ORM models.

Import every model module here so `Base.metadata` is complete when Alembic
autogenerates migrations.
"""

from app.models.base import Base

__all__ = ["Base"]
