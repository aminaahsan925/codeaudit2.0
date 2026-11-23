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
MIN_API_AUTH_TOKEN_LENGTH = 32

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
    cors_origins: CommaSeparatedList = Field(default_factory=lambda: ["http://localhost:3000"])
    max_request_bytes: int = Field(default=1_048_576, gt=0)
    # Live checks and journey runs may target loopback/private addresses
    # only when this is True AND the environment is not production.
    allow_loopback_live_checks: bool = False
    api_auth_token: SecretStr | None = None
    log_level: LogLevel = "INFO"
    app_version: str = "0.1.0"

    @field_validator("database_url")
    @classmethod
    def _check_database_url(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith(DATABASE_URL_SCHEME):
            raise ValueError(f"must use the {DATABASE_URL_SCHEME} scheme")
        return value

    @field_validator("api_auth_token", mode="before")
    @classmethod
    def _empty_token_is_unset(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

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
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must list explicit origins in production, not '*'")
        if self.api_auth_token is not None:
            problems.append(
                "API_AUTH_TOKEN must not be set in production: the shared-token auth stub "
                "is for development and test only"
            )
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


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
