"""Database engine and session factory.

Nothing here connects at import time: the engine is created lazily on first
use from `Settings.database_url`.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url.get_secret_value()
    # SQLite connections are single-threaded by default; the API serves
    # requests on a thread pool, so allow sharing the connection.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(
        url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args=connect_args,
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed.

    Uncommitted work is rolled back when the session closes; repositories or
    services commit explicitly.
    """
    with get_sessionmaker()() as session:
        yield session


def reset_engine() -> None:
    """Dispose the cached engine (tests, or after settings change)."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_sessionmaker.cache_clear()
    get_engine.cache_clear()
