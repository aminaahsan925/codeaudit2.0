"""Startup validation: sign-in must never fail silently.

`create_app` refuses to start when the production configuration would
break sign-in (no SESSION_SECRET, non-HTTPS origins or redirect URI), and
logs a loud warning outside production when SESSION_SECRET is missing
instead of letting sign-in disappear without a trace.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest

from app.core.config import Settings, SettingsError
from app.main import create_app

SettingsFactory = Callable[..., Settings]

TEST_SESSION_SECRET = "test-session-secret-for-startup-validation"  # noqa: S105 - test value
PRODUCTION_URLS = {
    "cors_origins": ["https://app.example.com"],
    "frontend_url": "https://app.example.com",
}


def test_production_without_session_secret_fails_startup(
    settings_factory: SettingsFactory,
) -> None:
    settings = settings_factory(environment="production", **PRODUCTION_URLS)

    with pytest.raises(SettingsError, match="SESSION_SECRET"):
        create_app(settings)


def test_production_http_frontend_url_fails_startup(
    settings_factory: SettingsFactory,
) -> None:
    settings = settings_factory(
        environment="production",
        cors_origins=["https://app.example.com"],
        session_secret=TEST_SESSION_SECRET,
    )

    with pytest.raises(SettingsError, match="FRONTEND_URL"):
        create_app(settings)


def test_production_http_cors_origin_fails_startup(
    settings_factory: SettingsFactory,
) -> None:
    settings = settings_factory(
        environment="production",
        cors_origins=["http://app.example.com"],
        frontend_url="https://app.example.com",
        session_secret=TEST_SESSION_SECRET,
    )

    with pytest.raises(SettingsError, match="CORS_ORIGINS"):
        create_app(settings)


def test_production_http_google_redirect_uri_fails_startup(
    settings_factory: SettingsFactory,
) -> None:
    settings = settings_factory(
        environment="production",
        session_secret=TEST_SESSION_SECRET,
        google_client_id="id.apps.googleusercontent.com",
        google_client_secret="test-google-client-secret",  # noqa: S106 - test value
        google_redirect_uri="http://api.example.com/auth/google/callback",
        **PRODUCTION_URLS,
    )

    with pytest.raises(SettingsError, match="GOOGLE_REDIRECT_URI"):
        create_app(settings)


def test_valid_production_config_starts(settings_factory: SettingsFactory) -> None:
    settings = settings_factory(
        environment="production",
        session_secret=TEST_SESSION_SECRET,
        google_client_id="id.apps.googleusercontent.com",
        google_client_secret="test-google-client-secret",  # noqa: S106 - test value
        google_redirect_uri="https://api.example.com/auth/google/callback",
        **PRODUCTION_URLS,
    )

    assert create_app(settings) is not None


def test_development_without_session_secret_warns_but_starts(
    settings_factory: SettingsFactory, caplog: pytest.LogCaptureFixture
) -> None:
    settings = settings_factory(environment="development", session_secret=None)

    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        app = create_app(settings)

    assert app is not None
    assert "SESSION_SECRET is not set" in caplog.text
    assert "sign-in is DISABLED" in caplog.text
