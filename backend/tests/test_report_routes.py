"""Tests for the report routes.

The router is not wired into `create_app` yet (the coordinator wires routers
at integration), so these tests mount it on a fresh app and override `get_db`
with a SQLite test session.
"""

from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routers import reports
from app.core.config import Settings
from app.db import get_db
from app.main import create_app
from app.models import Base
from app.repositories.audit_runs import AuditRunRepository
from app.repositories.findings import FindingRepository
from app.schemas.audit_run import AuditRun, AuditRunStatus, Verdict
from app.schemas.finding import (
    Confidence,
    Finding,
    FindingCategory,
    FindingEngine,
    Severity,
)

SHARE_TOKEN = "share-token-abc"  # noqa: S105

SettingsFactory = Callable[..., Settings]


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture
def report_client(session: Session, settings_factory: SettingsFactory) -> Iterator[TestClient]:
    app = create_app(settings_factory())
    app.include_router(reports.router, prefix="/api")

    def _override_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded_run(session: Session) -> AuditRun:
    runs = AuditRunRepository(session)
    findings = FindingRepository(session)
    run = runs.create(
        AuditRun(
            id=uuid4(),
            project_name="Demo app",
            status=AuditRunStatus.SUCCEEDED,
            verdict=Verdict.DO_NOT_LAUNCH,
            risk_score=8.3,
            share_token=SHARE_TOKEN,
            # A guest run: its report stays open by run id, and the PDF
            # still needs the dev token stub or the share token.
            is_guest=True,
        )
    )
    findings.create_many(
        run.id,
        [
            Finding(
                id=uuid4(),
                rule_id="DEBUG_MODE",
                engine=FindingEngine.NATIVE,
                category=FindingCategory.CONFIG,
                severity=Severity.LOW,
                confidence=Confidence.HIGH,
                title="Debug mode on",
                file="app.py",
                start_line=3,
                end_line=3,
            ),
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
                fix_guidance="Move the key to the environment.",
            ),
        ],
    )
    session.commit()
    return run


def auth_headers(api_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_token}"}


def test_get_report_returns_fix_first_findings(
    report_client: TestClient, seeded_run: AuditRun, api_token: str
) -> None:
    response = report_client.get(
        f"/api/runs/{seeded_run.id}/report", headers=auth_headers(api_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["id"] == str(seeded_run.id)
    assert body["run"]["verdict"] == "do_not_launch"
    assert body["run"]["risk_score"] == 8.3
    assert [f["rule_id"] for f in body["findings"]] == ["SECRET_GENERIC", "DEBUG_MODE"]
    assert body["counts"] == {"critical": 1, "high": 0, "medium": 0, "low": 1}
    # The seeded run has no journey steps stored.
    assert body["journey_steps"] == []
    assert body["previous_risk_score"] is None
    assert body["resolved_findings"] == []
    assert body["score_change"] is None


def test_get_report_is_public_without_auth(report_client: TestClient, seeded_run: AuditRun) -> None:
    # Report by run id is public (run ids are unguessable UUIDs), so a guest
    # who ran an audit can open its report from the link.
    response = report_client.get(f"/api/runs/{seeded_run.id}/report")

    assert response.status_code == 200
    assert response.json()["run"]["id"] == str(seeded_run.id)


def test_get_report_missing_run_is_404(report_client: TestClient, api_token: str) -> None:
    response = report_client.get(f"/api/runs/{uuid4()}/report", headers=auth_headers(api_token))

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Report not found."}}


def test_get_shared_report_is_public(report_client: TestClient, seeded_run: AuditRun) -> None:
    response = report_client.get(f"/api/reports/shared/{SHARE_TOKEN}")

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["id"] == str(seeded_run.id)
    assert [f["rule_id"] for f in body["findings"]] == ["SECRET_GENERIC", "DEBUG_MODE"]


def test_get_shared_report_unknown_token_is_404(report_client: TestClient) -> None:
    response = report_client.get("/api/reports/shared/no-such-token")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Report not found."}}


def test_get_pdf_with_auth(report_client: TestClient, seeded_run: AuditRun, api_token: str) -> None:
    response = report_client.get(
        f"/api/runs/{seeded_run.id}/report.pdf", headers=auth_headers(api_token)
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="launchaudit-report-{seeded_run.id}.pdf"'
    )
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 500


def test_get_pdf_with_share_token_and_no_auth(
    report_client: TestClient, seeded_run: AuditRun
) -> None:
    response = report_client.get(f"/api/runs/{seeded_run.id}/report.pdf?token={SHARE_TOKEN}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_get_pdf_without_auth_or_token_is_401(
    report_client: TestClient, seeded_run: AuditRun
) -> None:
    response = report_client.get(f"/api/runs/{seeded_run.id}/report.pdf")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "A valid bearer token or share token is required.",
        }
    }


def test_get_pdf_with_wrong_token_is_401(report_client: TestClient, seeded_run: AuditRun) -> None:
    response = report_client.get(f"/api/runs/{seeded_run.id}/report.pdf?token=wrong")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_pdf_with_wrong_bearer_is_401(report_client: TestClient, seeded_run: AuditRun) -> None:
    response = report_client.get(
        f"/api/runs/{seeded_run.id}/report.pdf",
        headers={"Authorization": "Bearer wrong"},
    )

    assert response.status_code == 401


def test_get_pdf_missing_run_is_404(report_client: TestClient, api_token: str) -> None:
    response = report_client.get(f"/api/runs/{uuid4()}/report.pdf", headers=auth_headers(api_token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
