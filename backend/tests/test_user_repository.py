"""User repository tests: create, look up by id/sub/email, update profile."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base
from app.repositories.users import UserRepository
from app.schemas.user import User


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture
def users(session: Session) -> UserRepository:
    return UserRepository(session)


def make_user(**overrides: object) -> User:
    values: dict[str, object] = {
        "id": uuid4(),
        "google_sub": "google-sub-123",
        "email": "amina@example.com",
        "name": "Amina",
        "picture_url": "https://example.com/pic.jpg",
        "is_demo": False,
        "created_at": datetime.now(UTC),
    }
    values.update(overrides)
    return User(**values)


def test_create_and_get_by_id(users: UserRepository) -> None:
    user = make_user()

    created = users.create(user)

    assert created.id == user.id
    assert users.get_by_id(user.id) == created


def test_get_by_google_sub(users: UserRepository) -> None:
    users.create(make_user())

    found = users.get_by_google_sub("google-sub-123")

    assert found is not None
    assert found.email == "amina@example.com"


def test_get_by_email(users: UserRepository) -> None:
    users.create(make_user())

    found = users.get_by_email("amina@example.com")

    assert found is not None
    assert found.google_sub == "google-sub-123"


def test_lookups_return_none_when_missing(users: UserRepository) -> None:
    assert users.get_by_id(uuid4()) is None
    assert users.get_by_google_sub("no-such-sub") is None
    assert users.get_by_email("nobody@example.com") is None


def test_duplicate_google_sub_is_rejected(users: UserRepository, session: Session) -> None:
    users.create(make_user())
    session.commit()

    with pytest.raises(IntegrityError):
        users.create(make_user(email="other@example.com"))


def test_duplicate_email_is_rejected(users: UserRepository, session: Session) -> None:
    users.create(make_user())
    session.commit()

    with pytest.raises(IntegrityError):
        users.create(make_user(google_sub="google-sub-999"))


def test_multiple_demo_users_without_google_sub(users: UserRepository) -> None:
    first = users.create(make_user(google_sub=None, email="demo1@launchaudit.local"))
    second = users.create(make_user(google_sub=None, email="demo2@launchaudit.local"))

    assert first.google_sub is None
    assert second.google_sub is None


def test_update_profile_refreshes_name_and_picture(users: UserRepository) -> None:
    user = users.create(make_user())

    updated = users.update_profile(
        user.id,
        email="amina.new@example.com",
        name="Amina Ahsan",
        picture_url="https://example.com/new-pic.jpg",
    )

    assert updated is not None
    assert updated.email == "amina.new@example.com"
    assert updated.name == "Amina Ahsan"
    assert updated.picture_url == "https://example.com/new-pic.jpg"
    assert updated.google_sub == "google-sub-123"
    assert updated.is_demo is False


def test_update_profile_returns_none_when_missing(users: UserRepository) -> None:
    assert users.update_profile(uuid4(), email="x@example.com", name=None, picture_url=None) is None
