"""Shared pytest setup.

The app is always built from injected `Settings`, so nothing here reads or
writes the process environment. Tests that exercise env loading use
`monkeypatch`, which restores the environment afterwards. No test here needs a
running database.
"""

from collections.abc import Callable, Iterator, Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings, settings_from_values
from app.main import create_app

# Fixed value for tests only; long enough to satisfy the minimum token length.
TEST_API_TOKEN = "test-api-token-0123456789abcdef0123456789"  # noqa: S105
TEST_DATABASE_URL = "postgresql+psycopg://launchaudit@localhost:5432/launchaudit_test"


@pytest.fixture(autouse=True)
def _fresh_settings() -> Iterator[None]:
    """Each test sees settings rebuilt from the current environment."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def api_token() -> str:
    return TEST_API_TOKEN


@pytest.fixture
def settings_factory() -> Callable[..., Settings]:
    """Build isolated `Settings` (no .env file, no ambient environment).

    The test token is only a default outside production, where settings forbid
    it; pass `api_auth_token` explicitly to override either way.
    """

    def build(**overrides: Any) -> Settings:
        values: dict[str, Any] = {
            "database_url": TEST_DATABASE_URL,
            "environment": "test",
        }
        if overrides.get("environment") != "production":
            values["api_auth_token"] = TEST_API_TOKEN
        values.update(overrides)
        return settings_from_values(**values)

    return build


@pytest.fixture
def client(settings_factory: Callable[..., Settings]) -> Iterator[TestClient]:
    with TestClient(create_app(settings_factory())) as test_client:
        yield test_client


@pytest.fixture
def make_client(settings_factory: Callable[..., Settings]) -> Callable[..., TestClient]:
    """Build a client for an app created from injected settings.

    Pass `routes=[(path, methods, endpoint)]` to register test-only routes on the
    app instance. Server exceptions become 500 responses instead of re-raising.
    """

    def build(
        routes: Sequence[tuple[str, list[str], Callable[..., Any]]] = (), **overrides: Any
    ) -> TestClient:
        app = create_app(settings_factory(**overrides))
        for path, methods, endpoint in routes:
            app.add_api_route(path, endpoint, methods=methods)
        return TestClient(app, raise_server_exceptions=False)

    return build
