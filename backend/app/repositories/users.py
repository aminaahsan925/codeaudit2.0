"""User repository: the only code that reads/writes `users`.

Public methods take and return Pydantic schemas (`app.schemas.user`);
ORM rows never leave this module. Writes are flushed, not committed: the
caller owns the transaction.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import UserModel
from app.repositories.base import BaseRepository
from app.schemas.user import User


def _dialect_insert(session: Session) -> Any:
    """The INSERT statement class for the session's database.

    ON CONFLICT upserts are dialect-specific: the generic `sqlalchemy.insert`
    has no `on_conflict_do_update`. SQLite (development and test) and
    Postgres (production) both support it through their own dialect class.
    """
    name = session.get_bind().dialect.name
    if name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    elif name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        raise RuntimeError(f"unsupported dialect for upsert: {name}")
    return dialect_insert


def _ensure_aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes; stored values are always UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _model_to_schema(model: UserModel) -> User:
    return User(
        id=model.id,
        google_sub=model.google_sub,
        email=model.email,
        name=model.name,
        picture_url=model.picture_url,
        is_demo=model.is_demo,
        created_at=_ensure_aware(model.created_at),
    )


class UserRepository(BaseRepository[UserModel]):
    """Create, read and update user accounts."""

    model = UserModel

    def get_by_id(self, user_id: UUID) -> User | None:
        model = super().get(user_id)
        return _model_to_schema(model) if model is not None else None

    def get_by_google_sub(self, google_sub: str) -> User | None:
        stmt = select(UserModel).where(UserModel.google_sub == google_sub)
        model = self.session.scalars(stmt).first()
        return _model_to_schema(model) if model is not None else None

    def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        model = self.session.scalars(stmt).first()
        return _model_to_schema(model) if model is not None else None

    def create(self, user: User) -> User:
        """Persist a new user."""
        instance = self.add(
            UserModel(
                id=user.id,
                google_sub=user.google_sub,
                email=user.email,
                name=user.name,
                picture_url=user.picture_url,
                is_demo=user.is_demo,
                created_at=user.created_at,
            )
        )
        return _model_to_schema(instance)

    def update_profile(
        self, user_id: UUID, *, email: str, name: str | None, picture_url: str | None
    ) -> User | None:
        """Refresh a user's profile from their latest sign-in. Returns None if missing."""
        model = super().get(user_id)
        if model is None:
            return None
        model.email = email
        model.name = name
        model.picture_url = picture_url
        self.session.flush()
        return _model_to_schema(model)

    def upsert_google_user(self, user: User) -> User:
        """Insert a Google account, or refresh its profile if it exists.

        One atomic statement (INSERT ... ON CONFLICT DO UPDATE on
        `google_sub`), so two sign-ins for a new account racing each other
        cannot produce an IntegrityError: exactly one row is created and the
        other call updates it. Works on SQLite and Postgres alike.
        """
        stmt = (
            _dialect_insert(self.session)(UserModel)
            .values(
                id=user.id,
                google_sub=user.google_sub,
                email=user.email,
                name=user.name,
                picture_url=user.picture_url,
                is_demo=False,
                created_at=user.created_at,
            )
            .on_conflict_do_update(
                index_elements=["google_sub"],
                set_={
                    "email": user.email,
                    "name": user.name,
                    "picture_url": user.picture_url,
                },
            )
            .returning(UserModel)
        )
        model = self.session.execute(stmt).scalar_one()
        return _model_to_schema(model)

    def get_or_create_demo_user(self, user: User) -> User:
        """Insert the single demo account, or return it if it already exists.

        INSERT ... ON CONFLICT DO NOTHING on `email`, so two demo sign-ins
        racing each other create exactly one row.
        """
        stmt = (
            _dialect_insert(self.session)(UserModel)
            .values(
                id=user.id,
                google_sub=None,
                email=user.email,
                name=user.name,
                picture_url=user.picture_url,
                is_demo=True,
                created_at=user.created_at,
            )
            .on_conflict_do_nothing(index_elements=["email"])
            .returning(UserModel)
        )
        model = self.session.execute(stmt).scalar_one_or_none()
        if model is not None:
            return _model_to_schema(model)
        existing = self.get_by_email(user.email)
        if existing is None:  # pragma: no cover - the row cannot vanish here
            raise RuntimeError("demo user vanished after a conflicting insert")
        return existing
