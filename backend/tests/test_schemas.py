from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.audit_run import AuditRun


def build_run(**overrides: Any) -> AuditRun:
    return AuditRun.model_validate({"id": uuid4(), "project_name": "demo", **overrides})


@pytest.mark.parametrize("field", ["repo_url", "live_url"])
@pytest.mark.parametrize(
    "url", ["https://github.com/acme/app", "http://localhost:3000/", "https://app.example.com"]
)
def test_http_and_https_urls_are_accepted(field: str, url: str) -> None:
    run = build_run(**{field: url})

    assert str(getattr(run, field)).startswith(url.split("://")[0] + "://")


@pytest.mark.parametrize("field", ["repo_url", "live_url"])
@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/repo",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "ssh://git@github.com/acme/app.git",
        "git@github.com:acme/app.git",
        "github.com/acme/app",
        "https://",
        "",
    ],
)
def test_non_http_urls_are_rejected(field: str, url: str) -> None:
    with pytest.raises(ValidationError):
        build_run(**{field: url})


@pytest.mark.parametrize("field", ["repo_url", "live_url"])
def test_urls_are_optional(field: str) -> None:
    assert getattr(build_run(), field) is None


def test_urls_serialise_as_strings() -> None:
    run = build_run(repo_url="https://github.com/acme/app", live_url="https://app.example.com/")

    dumped = run.model_dump(mode="json")

    assert dumped["repo_url"] == "https://github.com/acme/app"
    assert dumped["live_url"] == "https://app.example.com/"
