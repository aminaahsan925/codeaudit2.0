"""Assign-and-track-fixes tests: PATCH endpoint, rerun interplay, migration.

The endpoint tests drive the real app with `get_db` overridden by a SQLite
test session. The rerun tests run the real pipeline on the repo's demo zips
(broken -> fixed resolves everything; broken -> broken reproduces it).
The migration test runs Alembic itself against a fresh SQLite file.
"""

from __future__ import annotations

import secrets
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command as alembic_command
from app.core.config import Settings, get_settings
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
    FindingStatus,
    Severity,
    TrackingStatus,
)
from app.services.runs import execute_run
from tests.conftest import TEST_API_TOKEN

SettingsFactory = Callable[..., Settings]

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_DIR = BACKEND_DIR / "alembic"
REPO_DEMO_APP_DIR = BACKEND_DIR.parent / "demo-app"
PRE_TRACKING_REVISION = "1490bd5eba35"

SHARE_TOKEN = "share-token-for-tests"  # noqa: S105 - test-only value


# ------------------------------------------------------------------ fixtures


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
def api_client(settings_factory: SettingsFactory, db_session: Session) -> Iterator[TestClient]:
    app = create_app(settings_factory())
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client


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
    )


# ------------------------------------------------------------------- helpers


def make_run(**overrides: Any) -> AuditRun:
    values: dict[str, Any] = {
        "id": uuid4(),
        "project_name": "Demo app",
        "share_token": secrets.token_urlsafe(16),
        "is_guest": True,
    }
    values.update(overrides)
    return AuditRun(**values)


def make_finding(**overrides: Any) -> Finding:
    values: dict[str, Any] = {
        "id": uuid4(),
        "rule_id": "SECRET_GENERIC",
        "engine": FindingEngine.NATIVE,
        "category": FindingCategory.SECRETS,
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "Hardcoded secret",
        "file": "app.py",
        "start_line": 12,
        "end_line": 12,
    }
    values.update(overrides)
    return Finding(**values)


def _seed_run_with_finding(
    session: Session, *, is_guest: bool = True, owner: str | None = None
) -> tuple[AuditRun, Finding]:
    run = AuditRunRepository(session).create(make_run(is_guest=is_guest), owner=owner)
    finding = FindingRepository(session).create(run.id, make_finding())
    session.commit()
    return run, finding


def _zip_demo_tree(variant: str, dest: Path) -> Path:
    source = REPO_DEMO_APP_DIR / variant
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if (
                not path.is_file()
                or path.suffix in {".db"}
                or "__pycache__" in path.parts
                or "venv" in path.parts
                or ".venv" in path.parts
            ):
                continue
            archive.write(path, path.relative_to(source))
    return dest


def _create_run_row(session_factory: Callable[[], Session], **overrides: Any) -> AuditRun:
    run = make_run(**overrides)
    with session_factory() as session:
        created = AuditRunRepository(session).create(run)
        session.commit()
    return created


def _get_findings(session_factory: Callable[[], Session], run_id: UUID) -> list[Finding]:
    with session_factory() as session:
        return FindingRepository(session).list_for_run(run_id)


def _set_tracking(
    session_factory: Callable[[], Session],
    finding_id: UUID,
    *,
    assignee: str | None = None,
    tracking_status: TrackingStatus,
) -> None:
    with session_factory() as session:
        updated = FindingRepository(session).update_assignment(
            finding_id, assignee=assignee, tracking_status=tracking_status
        )
        assert updated is not None
        session.commit()


# ------------------------------------------------------------- PATCH endpoint


def test_patch_updates_assignee_and_status(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": "amina@example.com", "tracking_status": "in_progress"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assignee"] == "amina@example.com"
    assert body["tracking_status"] == "in_progress"
    assert body["id"] == str(finding.id)
    # Defaults for a fresh finding are unassigned and open.
    assert body["status"] == "open"


def test_patch_round_trips_through_report(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)
    api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": "Hadi", "tracking_status": "fixed"},
    )

    response = api_client.get(f"/api/runs/{run.id}/report")

    assert response.status_code == 200
    reported = response.json()["findings"][0]
    assert reported["assignee"] == "Hadi"
    assert reported["tracking_status"] == "fixed"


def test_patch_is_partial(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)
    api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": "amina@example.com", "tracking_status": "in_progress"},
    )

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"tracking_status": "ignored"},
    )

    assert response.status_code == 200
    assert response.json()["assignee"] == "amina@example.com"
    assert response.json()["tracking_status"] == "ignored"


def test_patch_clears_assignee(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)
    api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": "amina@example.com"},
    )

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": None},
    )

    assert response.status_code == 200
    assert response.json()["assignee"] is None


def test_patch_blank_assignee_clears(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)
    api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": "amina@example.com"},
    )

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": "   "},
    )

    assert response.status_code == 200
    assert response.json()["assignee"] is None


def test_patch_empty_body_is_a_noop(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)

    response = api_client.patch(f"/api/runs/{run.id}/findings/{finding.id}", json={})

    assert response.status_code == 200
    assert response.json()["assignee"] is None
    assert response.json()["tracking_status"] == "open"


def test_patch_rejects_unknown_tracking_status(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"tracking_status": "done"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
    # Nothing was written.
    stored = FindingRepository(db_session).get(finding.id)
    assert stored is not None
    assert stored.tracking_status == TrackingStatus.OPEN


def test_patch_rejects_overlong_assignee(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": "a" * 201},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_patch_accepts_200_char_assignee(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session)

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"assignee": "a" * 200},
    )

    assert response.status_code == 200
    assert response.json()["assignee"] == "a" * 200


def test_patch_unknown_finding_is_404(api_client: TestClient, db_session: Session) -> None:
    run, _ = _seed_run_with_finding(db_session)

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{uuid4()}",
        json={"tracking_status": "fixed"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_patch_finding_of_another_run_is_404(api_client: TestClient, db_session: Session) -> None:
    run, _ = _seed_run_with_finding(db_session)
    _, other_finding = _seed_run_with_finding(db_session)

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{other_finding.id}",
        json={"tracking_status": "fixed"},
    )

    assert response.status_code == 404


def test_patch_unknown_run_is_404(api_client: TestClient, db_session: Session) -> None:
    _, finding = _seed_run_with_finding(db_session)

    response = api_client.patch(
        f"/api/runs/{uuid4()}/findings/{finding.id}",
        json={"tracking_status": "fixed"},
    )

    assert response.status_code == 404


def test_patch_owned_run_needs_auth(api_client: TestClient, db_session: Session) -> None:
    run, finding = _seed_run_with_finding(db_session, is_guest=False)

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"tracking_status": "fixed"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_patch_owned_run_with_token_succeeds(api_client: TestClient, db_session: Session) -> None:
    # The dev token stub authenticates as principal "dev", so the run must
    # be owned by "dev" for the owner check to pass.
    run, finding = _seed_run_with_finding(db_session, is_guest=False, owner="dev")

    response = api_client.patch(
        f"/api/runs/{run.id}/findings/{finding.id}",
        json={"tracking_status": "fixed"},
        headers={"Authorization": f"Bearer {TEST_API_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json()["tracking_status"] == "fixed"


# ------------------------------------------------------------ rerun interplay


def test_rerun_auto_fixes_open_and_in_progress_only(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    tmp_path: Path,
) -> None:
    first = _create_run_row(session_factory)
    execute_run(
        first.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("broken", tmp_path / "broken.zip"),
    )
    first_findings = _get_findings(session_factory, first.id)
    assert len(first_findings) == 3
    by_rule = {finding.rule_id: finding for finding in first_findings}
    _set_tracking(
        session_factory,
        by_rule["SECRET_KNOWN_PREFIX"].id,
        assignee="amina@example.com",
        tracking_status=TrackingStatus.FIXED,
    )
    _set_tracking(
        session_factory,
        by_rule["WEAK_PASSWORD_RULE"].id,
        tracking_status=TrackingStatus.IGNORED,
    )
    _set_tracking(
        session_factory,
        by_rule["DEBUG_MODE"].id,
        assignee="hadi@example.com",
        tracking_status=TrackingStatus.IN_PROGRESS,
    )

    second = _create_run_row(session_factory, previous_run_id=first.id)
    execute_run(
        second.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("fixed", tmp_path / "fixed.zip"),
    )
    with session_factory() as session:
        assert AuditRunRepository(session).get(second.id) is not None
        assert AuditRunRepository(session).get(second.id).status == AuditRunStatus.SUCCEEDED

    after = {f.rule_id: f for f in _get_findings(session_factory, first.id)}
    # The rerun still marks every resolved finding fixed in the rerun status.
    assert {f.status for f in after.values()} == {FindingStatus.FIXED}
    # Manual fixed and ignored survive the rerun untouched.
    assert after["SECRET_KNOWN_PREFIX"].tracking_status == TrackingStatus.FIXED
    assert after["SECRET_KNOWN_PREFIX"].assignee == "amina@example.com"
    assert after["WEAK_PASSWORD_RULE"].tracking_status == TrackingStatus.IGNORED
    # In-progress was auto-marked fixed, keeping its assignee.
    assert after["DEBUG_MODE"].tracking_status == TrackingStatus.FIXED
    assert after["DEBUG_MODE"].assignee == "hadi@example.com"


def test_rerun_auto_fixes_open_finding(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    tmp_path: Path,
) -> None:
    first = _create_run_row(session_factory)
    execute_run(
        first.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("broken", tmp_path / "broken.zip"),
    )
    assert all(
        f.tracking_status == TrackingStatus.OPEN for f in _get_findings(session_factory, first.id)
    )

    second = _create_run_row(session_factory, previous_run_id=first.id)
    execute_run(
        second.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("fixed", tmp_path / "fixed.zip"),
    )

    after = _get_findings(session_factory, first.id)
    assert {f.tracking_status for f in after} == {TrackingStatus.FIXED}


def test_rerun_never_flips_manual_tracking_back(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    tmp_path: Path,
) -> None:
    # Same broken code twice: every finding is reproduced, so the rerun
    # resolves nothing. Manual fixed/ignored must stay exactly as set.
    first = _create_run_row(session_factory)
    execute_run(
        first.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("broken", tmp_path / "broken.zip"),
    )
    first_findings = _get_findings(session_factory, first.id)
    by_rule = {finding.rule_id: finding for finding in first_findings}
    _set_tracking(
        session_factory,
        by_rule["SECRET_KNOWN_PREFIX"].id,
        tracking_status=TrackingStatus.FIXED,
    )
    _set_tracking(
        session_factory,
        by_rule["WEAK_PASSWORD_RULE"].id,
        tracking_status=TrackingStatus.IGNORED,
    )

    second = _create_run_row(session_factory, previous_run_id=first.id)
    execute_run(
        second.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("broken", tmp_path / "broken.zip"),
    )

    after = {f.rule_id: f for f in _get_findings(session_factory, first.id)}
    assert after["SECRET_KNOWN_PREFIX"].tracking_status == TrackingStatus.FIXED
    assert after["WEAK_PASSWORD_RULE"].tracking_status == TrackingStatus.IGNORED
    assert after["DEBUG_MODE"].tracking_status == TrackingStatus.OPEN
    assert after["DEBUG_MODE"].status == FindingStatus.OPEN


# ------------------------------------------------------------------ migration


def _alembic_config() -> AlembicConfig:
    config = AlembicConfig()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    return config


def test_migration_up_and_down_on_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("API_AUTH_TOKEN", TEST_API_TOKEN)
    get_settings.cache_clear()
    config = _alembic_config()

    # Up to the revision before this feature, then seed one pre-existing row.
    alembic_command.upgrade(config, PRE_TRACKING_REVISION)
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        run_id = str(uuid4())
        connection.execute(
            text(
                "INSERT INTO audit_runs (id, project_name, status, progress, "
                "is_guest, domain_verified) "
                "VALUES (:id, 'Demo app', 'succeeded', 100, 1, 0)"
            ),
            {"id": run_id},
        )
        connection.execute(
            text(
                "INSERT INTO findings (id, run_id, rule_id, engine, category, "
                "severity, confidence, title, trace, evidence, status, finding_key) "
                "VALUES (:id, :run_id, 'SECRET_GENERIC', 'native', 'secrets', "
                "'critical', 'high', 'Hardcoded secret', '[]', '{}', 'open', 'k')"
            ),
            {"id": str(uuid4()), "run_id": run_id},
        )

    # Up to head: the new columns appear, and the old row is open/unassigned.
    alembic_command.upgrade(config, "head")
    columns = {c["name"] for c in inspect(engine).get_columns("findings")}
    assert "assignee" in columns
    assert "tracking_status" in columns
    with engine.connect() as connection:
        row = connection.execute(text("SELECT assignee, tracking_status FROM findings")).one()
    assert row[0] is None
    assert row[1] == "open"

    # Down one step: the columns are gone, the row survives.
    alembic_command.downgrade(config, PRE_TRACKING_REVISION)
    columns = {c["name"] for c in inspect(engine).get_columns("findings")}
    assert "assignee" not in columns
    assert "tracking_status" not in columns
    with engine.connect() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM findings")).scalar()
    assert count == 1

    # And back up again.
    alembic_command.upgrade(config, "head")
    columns = {c["name"] for c in inspect(engine).get_columns("findings")}
    assert "assignee" in columns
    assert "tracking_status" in columns
    engine.dispose()
