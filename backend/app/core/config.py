"""Application settings.

This module is the ONLY place in the backend that reads environment variables.
Everything else receives a `Settings` instance (via `get_settings()` or
`request.app.state.settings`).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BeforeValidator,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

DATABASE_URL_SCHEME = "postgresql+psycopg://"
SQLITE_DATABASE_URL_SCHEME = "sqlite://"
MIN_API_AUTH_TOKEN_LENGTH = 32
MIN_SESSION_SECRET_LENGTH = 32

Environment = Literal["development", "test", "production"]
LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


class SettingsError(RuntimeError):
    """Raised when the configuration is missing or invalid.

    The message names the offending variables but never includes their values.
    """


def _split_comma_separated(value: Any) -> Any:
    """Accept `a,b,c` (or a JSON array string) from the environment."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError("must be a comma-separated list or a JSON array") from exc
        else:
            value = stripped.split(",")
    if isinstance(value, list | tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    return value


CommaSeparatedList = Annotated[list[str], NoDecode, BeforeValidator(_split_comma_separated)]


class Settings(BaseSettings):
    """Typed, validated configuration loaded from env vars and `backend/.env`."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    # Required on purpose: a missing ENVIRONMENT must not silently mean "development".
    environment: Environment
    database_url: SecretStr
    cors_origins: CommaSeparatedList = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    max_request_bytes: int = Field(default=10_485_760, gt=0)
    api_auth_token: SecretStr | None = None
    log_level: LogLevel = "INFO"
    app_version: str = "0.1.0"
    artifact_dir: Path = BACKEND_DIR / "artifacts"
    allow_loopback_live_checks: bool = False
    gemini_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    audit_rate_limit_per_hour: int = Field(default=10, gt=0)
    # Google sign-in (all optional: the app runs fully without them, with
    # guest runs and demo sign-in instead). See docs/google-signin-setup.md.
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str | None = None
    # Signs session tokens (HS256). Unset or short means no session can be
    # issued, so sign-in is unavailable; it never fails open.
    session_secret: SecretStr | None = None
    # Public origin of the frontend; the Google callback redirects here.
    frontend_url: str = "http://localhost:3000"

    @field_validator("database_url")
    @classmethod
    def _check_database_url(cls, value: SecretStr) -> SecretStr:
        url = value.get_secret_value()
        if not (url.startswith(DATABASE_URL_SCHEME) or url.startswith(SQLITE_DATABASE_URL_SCHEME)):
            raise ValueError(
                f"must use the {DATABASE_URL_SCHEME} or {SQLITE_DATABASE_URL_SCHEME} scheme"
            )
        return value

    @field_validator("api_auth_token", mode="before")
    @classmethod
    def _empty_token_is_unset(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("gemini_api_key", "groq_api_key", mode="before")
    @classmethod
    def _empty_ai_key_is_unset(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "google_client_id",
        "google_client_secret",
        "google_redirect_uri",
        "session_secret",
        mode="before",
    )
    @classmethod
    def _empty_auth_value_is_unset(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("session_secret")
    @classmethod
    def _check_session_secret_strength(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < MIN_SESSION_SECRET_LENGTH:
            raise ValueError(f"must be at least {MIN_SESSION_SECRET_LENGTH} characters long")
        return value

    @field_validator("frontend_url")
    @classmethod
    def _check_frontend_url(cls, value: str) -> str:
        url = value.strip().rstrip("/")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("must be an absolute http(s) URL")
        return url

    @field_validator("api_auth_token")
    @classmethod
    def _check_token_strength(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < MIN_API_AUTH_TOKEN_LENGTH:
            raise ValueError(f"must be at least {MIN_API_AUTH_TOKEN_LENGTH} characters long")
        return value

    @field_validator("environment", mode="before")
    @classmethod
    def _normalise_environment(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _check_production_rules(self) -> Settings:
        if self.environment != "production":
            return self
        problems: list[str] = []
        if not self.database_url.get_secret_value().startswith(DATABASE_URL_SCHEME):
            problems.append(f"DATABASE_URL must use the {DATABASE_URL_SCHEME} scheme in production")
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must list explicit origins in production, not '*'")
        if self.api_auth_token is not None:
            problems.append(
                "API_AUTH_TOKEN must not be set in production: the shared-token auth stub "
                "is for development and test only"
            )
        if self.google_configured and self.session_secret is None:
            problems.append(
                "SESSION_SECRET must be set in production when Google sign-in is "
                "configured, or sign-in is silently unavailable"
            )
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def google_configured(self) -> bool:
        """True when all three Google OAuth values are set."""
        return bool(
            self.google_client_id and self.google_client_secret and self.google_redirect_uri
        )

    @property
    def sessions_available(self) -> bool:
        """True when session tokens can be issued (a secret is configured)."""
        return self.session_secret is not None


class _ExplicitSettings(Settings):
    """`Settings` that only accepts values passed to the constructor."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def settings_from_values(**values: Any) -> Settings:
    """Build validated settings from explicit values only.

    Neither environment variables nor `backend/.env` are consulted, so the result
    is fully determined by the arguments (scripts, tests). Raises
    `pydantic.ValidationError` on invalid values, like `Settings(...)`.
    """
    return _ExplicitSettings(**values)


def _describe_errors(exc: ValidationError) -> str:
    problems: list[str] = []
    for error in exc.errors(include_url=False, include_input=False, include_context=False):
        location = error.get("loc") or ()
        name = str(location[0]).upper() if location else ""
        if error.get("type") == "missing":
            detail = "is required but not set"
        else:
            detail = str(error.get("msg", "is invalid")).removeprefix("Value error, ")
        problems.append(f"{name} {detail}" if name else detail)
    return "; ".join(dict.fromkeys(problems))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once, failing fast with a readable, value-free message."""
    try:
        return Settings()  # type: ignore[call-arg]  # values come from the environment
    except ValidationError as exc:
        message = f"Invalid configuration: {_describe_errors(exc)}"
        raise SettingsError(message) from None
