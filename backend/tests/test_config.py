from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import MIN_API_AUTH_TOKEN_LENGTH, Settings, SettingsError, get_settings

DB_SECRET = "dbpass-s3cr3t-value"  # noqa: S105
TOKEN_SECRET = "api-token-s3cr3t-value-0123456789abcdef"  # noqa: S105
SHORT_TOKEN_SECRET = "short-s3cr3t-token"  # noqa: S105
VALID_DB_URL = f"postgresql+psycopg://app:{DB_SECRET}@db.internal:5432/launchaudit"

MakeClient = Callable[..., TestClient]
SettingsFactory = Callable[..., Settings]


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Isolate env loading: no backend/.env, no relevant variables, ENVIRONMENT=test.

    Tests set what they need through the returned monkeypatch, so every change
    is undone after the test.
    """
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in (
        "DATABASE_URL",
        "ENVIRONMENT",
        "CORS_ORIGINS",
        "API_AUTH_TOKEN",
        "MAX_REQUEST_BYTES",
        "LOG_LEVEL",
        "APP_VERSION",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENVIRONMENT", "test")
    return monkeypatch


def test_missing_database_url_fails_fast_naming_the_variable(
    clean_env: pytest.MonkeyPatch,
) -> None:
    clean_env.setenv("API_AUTH_TOKEN", TOKEN_SECRET)

    with pytest.raises(SettingsError) as excinfo:
        get_settings()

    assert "DATABASE_URL" in str(excinfo.value)
    assert TOKEN_SECRET not in str(excinfo.value)


def test_missing_database_url_error_has_no_chained_input(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("API_AUTH_TOKEN", TOKEN_SECRET)

    with pytest.raises(SettingsError) as excinfo:
        get_settings()

    assert excinfo.value.__cause__ is None
    assert TOKEN_SECRET not in repr(excinfo.value)


def test_wrong_database_scheme_does_not_leak_the_url(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", f"postgresql://app:{DB_SECRET}@db.internal/launchaudit")

    with pytest.raises(SettingsError) as excinfo:
        get_settings()

    message = str(excinfo.value)
    assert "DATABASE_URL" in message
    assert DB_SECRET not in message
    assert "db.internal" not in message


def test_invalid_values_name_variable_but_not_value(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("MAX_REQUEST_BYTES", "not-a-number-xyz")
    clean_env.setenv("LOG_LEVEL", "LOUDEST")

    with pytest.raises(SettingsError) as excinfo:
        get_settings()

    message = str(excinfo.value)
    assert "MAX_REQUEST_BYTES" in message
    assert "LOG_LEVEL" in message
    assert "not-a-number-xyz" not in message
    assert "LOUDEST" not in message
    assert DB_SECRET not in message


def test_non_positive_request_limit_is_rejected(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("MAX_REQUEST_BYTES", "0")

    with pytest.raises(SettingsError, match="MAX_REQUEST_BYTES"):
        get_settings()


def test_wildcard_cors_rejected_in_production(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("ENVIRONMENT", "production")
    clean_env.setenv("CORS_ORIGINS", "*")

    with pytest.raises(SettingsError) as excinfo:
        get_settings()

    message = str(excinfo.value)
    assert "CORS_ORIGINS" in message
    assert DB_SECRET not in message


def test_wildcard_among_other_origins_rejected_in_production(
    settings_factory: SettingsFactory,
) -> None:
    with pytest.raises(ValidationError):
        settings_factory(environment="production", cors_origins="https://a.example.com,*")


def test_wildcard_cors_is_not_rejected_outside_production(
    settings_factory: SettingsFactory,
) -> None:
    assert settings_factory(environment="development", cors_origins="*").cors_origins == ["*"]


def test_cors_origins_accepts_comma_separated(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("CORS_ORIGINS", "https://a.example.com, https://b.example.com ,,")

    assert get_settings().cors_origins == ["https://a.example.com", "https://b.example.com"]


def test_cors_origins_accepts_json_array(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("CORS_ORIGINS", '["https://a.example.com","https://b.example.com"]')

    assert get_settings().cors_origins == ["https://a.example.com", "https://b.example.com"]


def test_cors_origins_default(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)

    assert get_settings().cors_origins == ["http://localhost:3000"]


def test_defaults(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("ENVIRONMENT", "development")

    settings = get_settings()

    assert settings.environment == "development"
    assert settings.max_request_bytes == 1_048_576
    assert settings.api_auth_token is None
    assert settings.log_level == "INFO"
    assert settings.is_production is False


def test_environment_and_log_level_are_normalised(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("ENVIRONMENT", " Production ")
    clean_env.setenv("CORS_ORIGINS", "https://app.example.com")
    clean_env.setenv("LOG_LEVEL", "debug")

    settings = get_settings()

    assert settings.is_production is True
    assert settings.log_level == "DEBUG"


def test_empty_api_token_is_unset(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("API_AUTH_TOKEN", "")

    assert get_settings().api_auth_token is None


def test_secrets_are_hidden_in_repr(settings_factory: SettingsFactory) -> None:
    settings = settings_factory(database_url=VALID_DB_URL, api_auth_token=TOKEN_SECRET)

    assert DB_SECRET not in repr(settings)
    assert TOKEN_SECRET not in repr(settings)
    assert DB_SECRET not in str(settings)
    assert TOKEN_SECRET not in str(settings)


def test_settings_are_cached(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)

    assert get_settings() is get_settings()


@pytest.mark.parametrize("path", ["/api/docs", "/api/openapi.json"])
def test_production_disables_docs_and_schema(make_client: MakeClient, path: str) -> None:
    client = make_client(environment="production", cors_origins=["https://app.example.com"])

    response = client.get(path)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("path", ["/api/docs", "/api/openapi.json"])
def test_development_serves_docs_and_schema(make_client: MakeClient, path: str) -> None:
    assert make_client(environment="development").get(path).status_code == 200


def test_production_app_still_serves_the_api(make_client: MakeClient) -> None:
    client = make_client(environment="production", cors_origins=["https://app.example.com"])

    assert client.get("/api/health").status_code == 200


def test_production_cors_only_allows_configured_origins(make_client: MakeClient) -> None:
    client = make_client(environment="production", cors_origins=["https://app.example.com"])

    allowed = client.get("/api/health", headers={"Origin": "https://app.example.com"})
    other = client.get("/api/health", headers={"Origin": "https://evil.example.com"})

    assert allowed.headers["access-control-allow-origin"] == "https://app.example.com"
    assert "access-control-allow-origin" not in other.headers


def test_error_responses_never_contain_configured_secrets(
    settings_factory: SettingsFactory,
) -> None:
    from app.main import create_app

    settings = settings_factory(database_url=VALID_DB_URL, api_auth_token=TOKEN_SECRET)
    client = TestClient(create_app(settings))

    responses = [
        client.get("/api/auth/me"),
        client.get("/api/auth/me", headers={"Authorization": "Bearer nope"}),
        client.get("/api/missing"),
        client.post("/api/health"),
    ]

    for response in responses:
        assert DB_SECRET not in response.text
        assert TOKEN_SECRET not in response.text
        assert TOKEN_SECRET not in str(response.headers)


def test_missing_environment_fails_fast_naming_the_variable(
    clean_env: pytest.MonkeyPatch,
) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.delenv("ENVIRONMENT")

    with pytest.raises(SettingsError) as excinfo:
        get_settings()

    message = str(excinfo.value)
    assert "ENVIRONMENT is required but not set" in message
    assert DB_SECRET not in message


def test_environment_has_no_default() -> None:
    assert Settings.model_fields["environment"].is_required()


@pytest.mark.parametrize("value", ["", "staging", "prod"])
def test_unknown_environment_is_rejected(clean_env: pytest.MonkeyPatch, value: str) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("ENVIRONMENT", value)

    with pytest.raises(SettingsError, match="ENVIRONMENT"):
        get_settings()


def test_short_api_token_is_rejected_at_settings_load(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("API_AUTH_TOKEN", SHORT_TOKEN_SECRET)

    with pytest.raises(SettingsError) as excinfo:
        get_settings()

    message = str(excinfo.value)
    assert f"API_AUTH_TOKEN must be at least {MIN_API_AUTH_TOKEN_LENGTH} characters" in message
    assert SHORT_TOKEN_SECRET not in message
    assert DB_SECRET not in message


def test_api_token_length_boundary(settings_factory: SettingsFactory) -> None:
    with pytest.raises(ValidationError):
        settings_factory(api_auth_token="x" * (MIN_API_AUTH_TOKEN_LENGTH - 1))

    token = "x" * MIN_API_AUTH_TOKEN_LENGTH
    assert settings_factory(api_auth_token=token).api_auth_token.get_secret_value() == token


def test_api_token_in_production_is_rejected(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("ENVIRONMENT", "production")
    clean_env.setenv("CORS_ORIGINS", "https://app.example.com")
    clean_env.setenv("API_AUTH_TOKEN", TOKEN_SECRET)

    with pytest.raises(SettingsError) as excinfo:
        get_settings()

    message = str(excinfo.value)
    assert "API_AUTH_TOKEN must not be set in production" in message
    assert TOKEN_SECRET not in message
    assert DB_SECRET not in message


def test_blank_api_token_is_allowed_in_production(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", VALID_DB_URL)
    clean_env.setenv("ENVIRONMENT", "production")
    clean_env.setenv("CORS_ORIGINS", "https://app.example.com")
    clean_env.setenv("API_AUTH_TOKEN", "  ")

    settings = get_settings()

    assert settings.is_production is True
    assert settings.api_auth_token is None


def test_production_reports_all_rule_violations(settings_factory: SettingsFactory) -> None:
    with pytest.raises(ValidationError) as excinfo:
        settings_factory(environment="production", cors_origins="*", api_auth_token=TOKEN_SECRET)

    message = str(excinfo.value)
    assert "CORS_ORIGINS" in message
    assert "API_AUTH_TOKEN" in message
    assert TOKEN_SECRET not in message


def test_explicit_settings_ignore_the_environment(
    clean_env: pytest.MonkeyPatch, settings_factory: SettingsFactory
) -> None:
    clean_env.setenv("ENVIRONMENT", "production")
    clean_env.setenv("APP_VERSION", "9.9.9")
    clean_env.setenv("API_AUTH_TOKEN", SHORT_TOKEN_SECRET)

    settings = settings_factory(environment="development", api_auth_token=None)

    assert settings.environment == "development"
    assert settings.app_version == "0.1.0"
    assert settings.api_auth_token is None
