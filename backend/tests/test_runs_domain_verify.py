"""Run-time domain verification uses the stored server-issued token.

No servers are started here: the fetch is mocked where the runner calls
it (`verify_domain`), and the loopback path needs no fetch at all. The
demo flow (loopback URL, loopback allowed) still verifies with no token.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import Base
from app.repositories.audit_runs import AuditRunRepository
from app.repositories.domain_verifications import DomainVerificationRepository
from app.schemas.audit_run import AuditRun
from app.services.runs import runner as runner_module
from app.services.runs.runner import _verify_live_domain

SettingsFactory = Callable[..., Settings]

STORED_TOKEN = "server-issued-token-9d2f4b"  # noqa: S105 - fake test value


@pytest.fixture
def session_factory(tmp_path: Path) -> Iterator[Callable[[], Session]]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'runs.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield maker
    engine.dispose()


@pytest.fixture
def run_settings(settings_factory: SettingsFactory, tmp_path: Path) -> Settings:
    return settings_factory(
        database_url=f"sqlite:///{tmp_path / 'runs.db'}",
        artifact_dir=tmp_path / "artifacts",
        allow_loopback_live_checks=True,
    )


def _create_run(session_factory: Callable[[], Session], **overrides: Any) -> AuditRun:
    values: dict[str, Any] = {
        "id": uuid4(),
        "project_name": "Demo app",
        "share_token": secrets.token_urlsafe(16),
    }
    values.update(overrides)
    run = AuditRun(**values)
    with session_factory() as session:
        created = AuditRunRepository(session).create(run)
        session.commit()
    return created


def _get_run(session_factory: Callable[[], Session], run_id: UUID) -> AuditRun | None:
    with session_factory() as session:
        return AuditRunRepository(session).get(run_id)


def _issue_token(
    session_factory: Callable[[], Session],
    domain: str,
    owner: str | None,
    token: str = STORED_TOKEN,
) -> None:
    with session_factory() as session:
        DomainVerificationRepository(session).issue(domain, owner, token)
        session.commit()


def test_loopback_demo_run_verifies_with_no_token(
    session_factory: Callable[[], Session], run_settings: Settings
) -> None:
    run = _create_run(session_factory, live_url="http://127.0.0.1:8001/")

    verified = _verify_live_domain(run, run_settings, session_factory, None)

    assert verified is True
    assert _get_run(session_factory, run.id).domain_verified is True


def test_loopback_run_without_loopback_allowed_does_not_verify(
    session_factory: Callable[[], Session],
    settings_factory: SettingsFactory,
    tmp_path: Path,
) -> None:
    settings = settings_factory(
        database_url=f"sqlite:///{tmp_path / 'runs.db'}",
        artifact_dir=tmp_path / "artifacts",
        allow_loopback_live_checks=False,
    )
    run = _create_run(session_factory, live_url="http://127.0.0.1:8001/")

    assert _verify_live_domain(run, settings, session_factory, None) is False
    assert _get_run(session_factory, run.id).domain_verified is False


def test_public_domain_without_stored_token_does_not_verify(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _must_not_fetch(*args: Any, **kwargs: Any) -> bool:
        raise AssertionError("verify_domain must not run without a stored token")

    monkeypatch.setattr(runner_module, "verify_domain", _must_not_fetch)
    run = _create_run(session_factory, live_url="https://shop.example.com")

    assert _verify_live_domain(run, run_settings, session_factory, None) is False
    assert _get_run(session_factory, run.id).domain_verified is False


def test_public_domain_verifies_with_stored_token(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def _fake_verify(url: str, token: str, settings: Settings) -> bool:
        calls.append((url, token))
        return True

    monkeypatch.setattr(runner_module, "verify_domain", _fake_verify)
    _issue_token(session_factory, "shop.example.com", None)
    run = _create_run(session_factory, live_url="https://shop.example.com")

    verified = _verify_live_domain(run, run_settings, session_factory, None)

    assert verified is True
    assert calls == [("https://shop.example.com/", STORED_TOKEN)]
    assert _get_run(session_factory, run.id).domain_verified is True


def test_public_domain_uses_owner_scoped_token(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def _fake_verify(url: str, token: str, settings: Settings) -> bool:
        calls.append((url, token))
        return True

    monkeypatch.setattr(runner_module, "verify_domain", _fake_verify)
    _issue_token(session_factory, "shop.example.com", "alice@example.com")
    run = _create_run(session_factory, live_url="https://shop.example.com")

    assert _verify_live_domain(run, run_settings, session_factory, "bob@example.com") is False
    assert calls == []

    assert _verify_live_domain(run, run_settings, session_factory, "alice@example.com") is True
    assert calls == [("https://shop.example.com/", STORED_TOKEN)]


def test_guest_token_is_not_used_for_signed_in_run(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _must_not_fetch(*args: Any, **kwargs: Any) -> bool:
        raise AssertionError("a guest token must not verify a signed-in run")

    monkeypatch.setattr(runner_module, "verify_domain", _must_not_fetch)
    _issue_token(session_factory, "shop.example.com", None)
    run = _create_run(session_factory, live_url="https://shop.example.com")

    assert _verify_live_domain(run, run_settings, session_factory, "alice@example.com") is False


def test_failed_stored_token_check_does_not_verify(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "verify_domain", lambda *a, **k: False)
    _issue_token(session_factory, "shop.example.com", None)
    run = _create_run(session_factory, live_url="https://shop.example.com")

    assert _verify_live_domain(run, run_settings, session_factory, None) is False
    assert _get_run(session_factory, run.id).domain_verified is False
