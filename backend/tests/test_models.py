import sqlite3
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AuditRunModel, Base, FindingModel

SHARE_TOKEN = "share-token-abc"  # noqa: S105


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: sqlite3.Connection, _: object) -> None:
        # SQLite does not enforce foreign keys unless asked.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


def make_run(**overrides: object) -> AuditRunModel:
    values: dict[str, object] = {"project_name": "Demo app"}
    values.update(overrides)
    return AuditRunModel(**values)


def make_finding(run_id: object, **overrides: object) -> FindingModel:
    values: dict[str, object] = {
        "run_id": run_id,
        "rule_id": "SECRET_GENERIC",
        "engine": "native",
        "category": "secrets",
        "severity": "critical",
        "confidence": "high",
        "title": "Hardcoded secret",
        "finding_key": "SECRET_GENERIC|app.py:12",
    }
    values.update(overrides)
    return FindingModel(**values)


def test_run_defaults(session: Session) -> None:
    run = make_run()
    session.add(run)
    session.commit()

    assert run.id is not None
    assert run.status == "queued"
    assert run.progress == 0
    assert run.verdict is None
    assert run.risk_score is None
    assert run.started_at is None
    assert run.finished_at is None
    assert run.error is None
    assert run.share_token is None
    assert run.is_guest is False
    assert run.owner is None


def test_run_round_trip(session: Session) -> None:
    run = make_run(
        project_name="Shop",
        repo_url="https://github.com/example/shop",
        live_url="https://shop.example.com",
        share_token=SHARE_TOKEN,
        is_guest=True,
        owner="user-1",
    )
    session.add(run)
    session.commit()
    session.expire_all()

    stored = session.get(AuditRunModel, run.id)

    assert stored is not None
    assert stored.project_name == "Shop"
    assert stored.repo_url == "https://github.com/example/shop"
    assert stored.live_url == "https://shop.example.com"
    assert stored.share_token == SHARE_TOKEN
    assert stored.is_guest is True
    assert stored.owner == "user-1"


def test_share_token_is_unique(session: Session) -> None:
    session.add(make_run(share_token=SHARE_TOKEN))
    session.add(make_run(share_token=SHARE_TOKEN))

    with pytest.raises(IntegrityError):
        session.commit()


def test_finding_defaults(session: Session) -> None:
    run = make_run()
    session.add(run)
    session.flush()
    finding = make_finding(run.id)
    session.add(finding)
    session.commit()

    assert finding.id is not None
    assert finding.status == "open"
    assert finding.trace == []
    assert finding.evidence == {}
    assert finding.ai_verdict is None
    assert finding.cwe is None
    assert finding.file is None
    assert finding.start_line is None
    assert finding.end_line is None
    assert finding.snippet is None
    assert finding.fix_guidance is None


def test_finding_json_columns_round_trip(session: Session) -> None:
    run = make_run()
    session.add(run)
    session.flush()
    finding = make_finding(
        run.id,
        trace=[{"file": "app.py", "line": 3, "snippet": "x = req", "label": "source"}],
        evidence={"notes": "Step: Check out", "secret_preview": "sk_live_****"},
        ai_verdict={"verdict": "confirmed", "reason": "real", "quoted_code": "x = 1"},
    )
    session.add(finding)
    session.commit()
    session.expire_all()

    stored = session.get(FindingModel, finding.id)

    assert stored is not None
    assert stored.trace == [{"file": "app.py", "line": 3, "snippet": "x = req", "label": "source"}]
    assert stored.evidence == {"notes": "Step: Check out", "secret_preview": "sk_live_****"}
    assert stored.ai_verdict == {
        "verdict": "confirmed",
        "reason": "real",
        "quoted_code": "x = 1",
    }


def test_deleting_run_deletes_its_findings(session: Session) -> None:
    run = make_run()
    session.add(run)
    session.flush()
    session.add(make_finding(run.id))
    session.add(make_finding(run.id, rule_id="DEBUG_MODE", finding_key="DEBUG_MODE|app.py:1"))
    session.commit()

    session.delete(run)
    session.commit()

    assert session.scalars(select(FindingModel)).all() == []


def test_finding_requires_an_existing_run(session: Session) -> None:
    session.add(make_finding(uuid4()))

    with pytest.raises(IntegrityError):
        session.commit()
