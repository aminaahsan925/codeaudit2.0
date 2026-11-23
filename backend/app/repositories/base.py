"""Generic repository: the only layer that talks to the database.

Queries are built with SQLAlchemy constructs, so every value is a bound
parameter. Never build SQL with f-strings or string concatenation.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.base import Base


class BaseRepository[ModelT: Base]:
    """CRUD helpers for one ORM model. Subclasses set `model`."""

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, ident: Any) -> ModelT | None:
        return self.session.get(self.model, ident)

    def list_page(self, *, limit: int = 50, offset: int = 0) -> Sequence[ModelT]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        primary_key = inspect(self.model).primary_key
        stmt = select(self.model).order_by(*primary_key).limit(limit).offset(offset)
        return self.session.scalars(stmt).all()

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()
