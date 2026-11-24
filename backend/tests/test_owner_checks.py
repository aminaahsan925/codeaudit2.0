"""Owner checks: an owned run is visible only to its owner.

No token at all is a 401. A signed-in user who is not the owner gets a
404, identical to a missing run, so the run's existence stays hidden.
Guest runs stay open by run id, shared reports stay public by share
token, and artifacts accept a share token so the screenshots on a shared
report page keep loading without a login.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routers import runs as runs_router
from app.core.config import Settings
from app.core.ratelimit import reset as reset_rate_limits
from app.core.security import issue_session_token
from app.db import get_db
from app.main import create_app
from app.models import Base
from app.repositories.audit_runs import AuditRunRepository
from app.repositories.findings import FindingRepository
from app.schemas.audit_run import AuditRun, AuditRunStatus
from app.schemas.finding import (
    Confidence,
    Finding,
    FindingCategory,
    FindingEngine,
    Severity,
)
from tests.conftest import TEST_API_TOKEN

SettingsFactory = Callable[..., Settings]

# Fixed value for tests only; long enough to satisfy the minimum secret length.
TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef0123456789"  # noqa: S105

OWNER_EMAIL = "owner@example.com"
OTHER_EMAIL = "other@example.com"
OWNER_SHARE_TOKEN = "owner-share-token"  # noqa: S105
GUEST_SHARE_TOKEN = "guest-share-token"  # noqa: S105


def _session_token(email: str) -> str:
    return issue_session_token(
        TEST_SESSION_SECRET,
        user_id=uuid4(),
        email=email,
        name=None,
        picture_url=None,
        demo=False,
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> Iterator[None]:
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def db_session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with maker() as session:
        yield session
    engine.dispose()


@pytest.fixture
def run_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Stub execute_run: record the call instead of running the pipeline."""
    calls: list[dict[str, Any]] = []

    def fake_execute_run(
        run_id: UUID,
        settings: Settings,
        review_fn: object | None = None,
        **kwargs: Any,
    ) -> None:
        calls.append({"run_id": run_id, "settings": settings, **kwargs})

    monkeypatch.setattr(runs_router, "execute_run", fake_execute_run)
    return calls


@pytest.fixture
def client(settings_factory: SettingsFactory, db_session: Session, tmp_path: Path) -> TestClient:
    settings = settings_factory(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        artifact_dir=tmp_path / "artifacts",
        session_secret=TEST_SESSION_SECRET,
    )
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def owned_run(db_session: Session) -> AuditRun:
    run = AuditRunRepository(db_session).create(
        AuditRun(
            id=uuid4(),
            project_name="Owned shop",
            status=AuditRunStatus.SUCCEEDED,
            share_token=OWNER_SHARE_TOKEN,
            is_guest=False,
        ),
        owner=OWNER_EMAIL,
    )
    db_session.commit()
    return run


@pytest.fixture
def guest_run(db_session: Session) -> AuditRun:
    run = AuditRunRepository(db_session).create(
        AuditRun(
            id=uuid4(),
            project_name="Guest shop",
            status=AuditRunStatus.SUCCEEDED,
            share_token=GUEST_SHARE_TOKEN,
            is_guest=True,
        )
    )
    db_session.commit()
    return run


@pytest.fixture
def owned_finding(db_session: Session, owned_run: AuditRun) -> Finding:
    finding = FindingRepository(db_session).create(
        owned_run.id,
        Finding(
            id=uuid4(),
            rule_id="SECRET_GENERIC",
            engine=FindingEngine.NATIVE,
            category=FindingCategory.SECRETS,
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            title="Hardcoded secret",
            file="app.py",
            start_line=12,
            end_line=12,
        ),
    )
    db_session.commit()
    return finding


@pytest.fixture
def guest_finding(db_session: Session, guest_run: AuditRun) -> Finding:
    finding = FindingRepository(db_session).create(
        guest_run.id,
        Finding(
            id=uuid4(),
            rule_id="SECRET_GENERIC",
            engine=FindingEngine.NATIVE,
            category=FindingCategory.SECRETS,
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            title="Hardcoded secret",
            file="app.py",
            start_line=12,
            end_line=12,
        ),
    )
    db_session.commit()
    return finding


def _seed_artifact(tmp_path: Path, run_id: UUID) -> None:
    artifact_dir = tmp_path / "artifacts" / str(run_id)
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "step-04-checkout.png").write_bytes(b"\x89PNG fake image")


# ------------------------------------------------------------------- get run


def test_get_run_owner_is_200(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(f"/api/runs/{owned_run.id}", headers=_auth(_session_token(OWNER_EMAIL)))

    assert response.status_code == 200
    assert response.json()["id"] == str(owned_run.id)


def test_get_run_other_user_is_404(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(f"/api/runs/{owned_run.id}", headers=_auth(_session_token(OTHER_EMAIL)))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_run_no_auth_is_401(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(f"/api/runs/{owned_run.id}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_run_dev_token_is_not_the_owner(client: TestClient, owned_run: AuditRun) -> None:
    # The dev stub principal ("dev") must not pass as the owner of a real
    # user's run.
    response = client.get(f"/api/runs/{owned_run.id}", headers=_auth(TEST_API_TOKEN))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_guest_run_without_auth_is_200(client: TestClient, guest_run: AuditRun) -> None:
    response = client.get(f"/api/runs/{guest_run.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(guest_run.id)


# -------------------------------------------------------------------- report


def test_get_report_owner_is_200(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(
        f"/api/runs/{owned_run.id}/report", headers=_auth(_session_token(OWNER_EMAIL))
    )

    assert response.status_code == 200
    assert response.json()["run"]["id"] == str(owned_run.id)


def test_get_report_other_user_is_404(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(
        f"/api/runs/{owned_run.id}/report", headers=_auth(_session_token(OTHER_EMAIL))
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_report_no_auth_is_401(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(f"/api/runs/{owned_run.id}/report")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_guest_report_without_auth_is_200(client: TestClient, guest_run: AuditRun) -> None:
    response = client.get(f"/api/runs/{guest_run.id}/report")

    assert response.status_code == 200
    assert response.json()["run"]["id"] == str(guest_run.id)


# ----------------------------------------------------------------- artifacts


def test_get_artifact_owner_is_200(client: TestClient, owned_run: AuditRun, tmp_path: Path) -> None:
    _seed_artifact(tmp_path, owned_run.id)

    response = client.get(
        f"/api/runs/{owned_run.id}/artifacts/step-04-checkout.png",
        headers=_auth(_session_token(OWNER_EMAIL)),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG fake image"


def test_get_artifact_other_user_is_404(
    client: TestClient, owned_run: AuditRun, tmp_path: Path
) -> None:
    _seed_artifact(tmp_path, owned_run.id)

    response = client.get(
        f"/api/runs/{owned_run.id}/artifacts/step-04-checkout.png",
        headers=_auth(_session_token(OTHER_EMAIL)),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_artifact_no_auth_is_401(
    client: TestClient, owned_run: AuditRun, tmp_path: Path
) -> None:
    _seed_artifact(tmp_path, owned_run.id)

    response = client.get(f"/api/runs/{owned_run.id}/artifacts/step-04-checkout.png")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_artifact_with_share_token_without_auth_is_200(
    client: TestClient, owned_run: AuditRun, tmp_path: Path
) -> None:
    _seed_artifact(tmp_path, owned_run.id)

    response = client.get(
        f"/api/runs/{owned_run.id}/artifacts/step-04-checkout.png?token={OWNER_SHARE_TOKEN}"
    )

    assert response.status_code == 200
    assert response.content == b"\x89PNG fake image"


def test_get_artifact_with_wrong_share_token_is_401(
    client: TestClient, owned_run: AuditRun, tmp_path: Path
) -> None:
    _seed_artifact(tmp_path, owned_run.id)

    response = client.get(f"/api/runs/{owned_run.id}/artifacts/step-04-checkout.png?token=wrong")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_guest_artifact_without_auth_is_200(
    client: TestClient, guest_run: AuditRun, tmp_path: Path
) -> None:
    _seed_artifact(tmp_path, guest_run.id)

    response = client.get(f"/api/runs/{guest_run.id}/artifacts/step-04-checkout.png")

    assert response.status_code == 200
    assert response.content == b"\x89PNG fake image"


def test_get_artifact_missing_run_is_404(client: TestClient) -> None:
    response = client.get(f"/api/runs/{uuid4()}/artifacts/step-04-checkout.png")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --------------------------------------------------------------------- rerun


def test_rerun_owner_is_201(
    client: TestClient, owned_run: AuditRun, run_calls: list[dict[str, Any]]
) -> None:
    response = client.post(
        f"/api/runs/{owned_run.id}/rerun",
        json={},
        headers=_auth(_session_token(OWNER_EMAIL)),
    )

    assert response.status_code == 201
    assert response.json()["previous_run_id"] == str(owned_run.id)
    assert response.json()["is_guest"] is False
    assert len(run_calls) == 1


def test_rerun_other_user_is_404(
    client: TestClient, owned_run: AuditRun, run_calls: list[dict[str, Any]]
) -> None:
    response = client.post(
        f"/api/runs/{owned_run.id}/rerun",
        json={},
        headers=_auth(_session_token(OTHER_EMAIL)),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert run_calls == []


def test_rerun_no_auth_is_401(client: TestClient, owned_run: AuditRun) -> None:
    response = client.post(f"/api/runs/{owned_run.id}/rerun", json={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_rerun_guest_without_auth_is_201(
    client: TestClient, guest_run: AuditRun, run_calls: list[dict[str, Any]]
) -> None:
    response = client.post(f"/api/runs/{guest_run.id}/rerun", json={})

    assert response.status_code == 201
    assert response.json()["is_guest"] is True
    assert len(run_calls) == 1


# ------------------------------------------------------------------ findings


def test_patch_finding_owner_is_200(
    client: TestClient, owned_run: AuditRun, owned_finding: Finding
) -> None:
    response = client.patch(
        f"/api/runs/{owned_run.id}/findings/{owned_finding.id}",
        json={"tracking_status": "fixed"},
        headers=_auth(_session_token(OWNER_EMAIL)),
    )

    assert response.status_code == 200
    assert response.json()["tracking_status"] == "fixed"


def test_patch_finding_other_user_is_404(
    client: TestClient, owned_run: AuditRun, owned_finding: Finding
) -> None:
    response = client.patch(
        f"/api/runs/{owned_run.id}/findings/{owned_finding.id}",
        json={"tracking_status": "fixed"},
        headers=_auth(_session_token(OTHER_EMAIL)),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_patch_finding_no_auth_is_401(
    client: TestClient, owned_run: AuditRun, owned_finding: Finding
) -> None:
    response = client.patch(
        f"/api/runs/{owned_run.id}/findings/{owned_finding.id}",
        json={"tracking_status": "fixed"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_patch_guest_finding_without_auth_is_200(
    client: TestClient, guest_run: AuditRun, guest_finding: Finding
) -> None:
    response = client.patch(
        f"/api/runs/{guest_run.id}/findings/{guest_finding.id}",
        json={"tracking_status": "fixed"},
    )

    assert response.status_code == 200
    assert response.json()["tracking_status"] == "fixed"


# ------------------------------------------------------- shared report + pdf


def test_shared_report_still_public_without_auth(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(f"/api/reports/shared/{OWNER_SHARE_TOKEN}")

    assert response.status_code == 200
    assert response.json()["run"]["id"] == str(owned_run.id)


def test_get_pdf_owner_session_token_is_200(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(
        f"/api/runs/{owned_run.id}/report.pdf",
        headers=_auth(_session_token(OWNER_EMAIL)),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_get_pdf_other_user_is_401(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(
        f"/api/runs/{owned_run.id}/report.pdf",
        headers=_auth(_session_token(OTHER_EMAIL)),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_pdf_share_token_still_works(client: TestClient, owned_run: AuditRun) -> None:
    response = client.get(f"/api/runs/{owned_run.id}/report.pdf?token={OWNER_SHARE_TOKEN}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_get_pdf_dev_token_still_works_in_non_production(
    client: TestClient, owned_run: AuditRun
) -> None:
    response = client.get(f"/api/runs/{owned_run.id}/report.pdf", headers=_auth(TEST_API_TOKEN))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
