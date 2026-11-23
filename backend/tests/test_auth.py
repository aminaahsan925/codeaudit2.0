from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

MakeClient = Callable[..., TestClient]
SettingsFactory = Callable[..., Settings]


def assert_unauthorized(response: Any) -> None:
    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "unauthorized", "message": "Missing or invalid bearer token."}
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_valid_token(client: TestClient, api_token: str) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {api_token}"})

    assert response.status_code == 200
    assert response.json() == {"subject": "dev"}


def test_me_without_header_is_401(client: TestClient) -> None:
    assert_unauthorized(client.get("/api/auth/me"))


def test_me_with_wrong_scheme_is_401(client: TestClient, api_token: str) -> None:
    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": f"Basic {api_token}"}))


def test_me_with_raw_token_and_no_scheme_is_401(client: TestClient, api_token: str) -> None:
    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": api_token}))


def test_me_with_wrong_token_is_401(client: TestClient) -> None:
    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": "Bearer wrong"}))


def test_me_with_near_miss_tokens_is_401(client: TestClient, api_token: str) -> None:
    for candidate in (api_token[:-1], api_token + "x", api_token.upper()):
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {candidate}"})
        assert_unauthorized(response)


def test_me_with_empty_bearer_is_401(client: TestClient) -> None:
    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": "Bearer "}))


@pytest.mark.parametrize("token", ["some-token", "dev"])
def test_unset_token_rejects_any_presented_token(make_client: MakeClient, token: str) -> None:
    client = make_client(api_auth_token=None)

    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}))


def test_unset_token_rejects_missing_header(make_client: MakeClient) -> None:
    assert_unauthorized(make_client(api_auth_token=None).get("/api/auth/me"))


def test_blank_configured_token_is_treated_as_unset(make_client: MakeClient) -> None:
    client = make_client(api_auth_token="   ")  # noqa: S106

    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": "Bearer    "}))
    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": "Bearer x"}))


def test_rejection_does_not_leak_the_configured_token(client: TestClient, api_token: str) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer wrong"})

    assert api_token not in response.text
    assert api_token not in str(response.headers)


def test_require_auth_rejects_in_production_even_with_a_configured_token(
    settings_factory: SettingsFactory, api_token: str
) -> None:
    # Settings validation forbids this combination; model_copy skips validation to
    # prove the dependency itself refuses to authenticate in production.
    settings = settings_factory().model_copy(update={"environment": "production"})
    assert settings.is_production
    assert settings.api_auth_token is not None

    client = TestClient(create_app(settings))
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {api_token}"})

    assert_unauthorized(response)
    assert api_token not in response.text


def test_require_auth_rejects_in_production_without_a_token(make_client: MakeClient) -> None:
    client = make_client(environment="production", cors_origins=["https://app.example.com"])

    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": "Bearer anything"}))
