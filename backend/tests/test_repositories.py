from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from app.repositories.audit_runs import AuditRunRepository
from app.repositories.findings import FindingRepository, finding_key_for
from app.schemas.audit_run import AuditRun, AuditRunStatus, Verdict
from app.schemas.finding import (
    AIVerdict,
    AIVerdictLabel,
    Confidence,
    Evidence,
    Finding,
    FindingCategory,
    FindingEngine,
    FindingStatus,
    HttpEvidence,
    Severity,
    TraceStep,
)

SHARE_TOKEN = "share-token-abc"  # noqa: S105
SECRET_PREVIEW = "sk_live_****"  # noqa: S105


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
def runs(session: Session) -> AuditRunRepository:
    return AuditRunRepository(session)


@pytest.fixture
def findings(session: Session) -> FindingRepository:
    return FindingRepository(session)


def make_run(**overrides: object) -> AuditRun:
    values: dict[str, object] = {"id": uuid4(), "project_name": "Demo app"}
    values.update(overrides)
    return AuditRun(**values)


def make_finding(**overrides: object) -> Finding:
    values: dict[str, object] = {
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


def test_create_and_get_run(runs: AuditRunRepository, session: Session) -> None:
    run = make_run(
        repo_url="https://github.com/example/shop",
        live_url="https://shop.example.com",
        share_token=SHARE_TOKEN,
        is_guest=True,
    )

    created = runs.create(run, owner="user-1")
    session.commit()

    assert created.id == run.id
    assert created.project_name == "Demo app"
    assert created.repo_url == run.repo_url
    assert created.live_url == run.live_url
    assert created.status == AuditRunStatus.QUEUED
    assert created.progress == 0
    assert created.share_token == SHARE_TOKEN
    assert created.is_guest is True

    stored = runs.get(run.id)
    assert stored == created


def test_get_missing_run_returns_none(runs: AuditRunRepository) -> None:
    assert runs.get(uuid4()) is None


def test_get_run_by_share_token(runs: AuditRunRepository) -> None:
    run = runs.create(make_run(share_token=SHARE_TOKEN))

    assert runs.get_by_share_token(SHARE_TOKEN) == run
    assert runs.get_by_share_token("no-such-token") is None


def test_update_run_status(runs: AuditRunRepository) -> None:
    run = runs.create(make_run())
    started = datetime(2026, 11, 24, 1, 0, tzinfo=UTC)

    updated = runs.update_status(
        run.id, status=AuditRunStatus.RUNNING, progress=40, started_at=started
    )

    assert updated is not None
    assert updated.status == AuditRunStatus.RUNNING
    assert updated.progress == 40
    assert updated.started_at == started
    assert updated.error is None


def test_update_run_status_records_failure(runs: AuditRunRepository) -> None:
    run = runs.create(make_run())
    finished = datetime(2026, 11, 24, 1, 5, tzinfo=UTC)

    updated = runs.update_status(
        run.id,
        status=AuditRunStatus.FAILED,
        progress=100,
        error="Clone failed.",
        finished_at=finished,
    )

    assert updated is not None
    assert updated.status == AuditRunStatus.FAILED
    assert updated.error == "Clone failed."
    assert updated.finished_at == finished


def test_update_missing_run_returns_none(runs: AuditRunRepository) -> None:
    assert runs.update_status(uuid4(), status=AuditRunStatus.RUNNING) is None
    assert runs.update_result(uuid4(), verdict=Verdict.LAUNCH, risk_score=1.0) is None


def test_update_run_result(runs: AuditRunRepository) -> None:
    run = runs.create(make_run())

    updated = runs.update_result(run.id, verdict=Verdict.DO_NOT_LAUNCH, risk_score=8.3)

    assert updated is not None
    assert updated.verdict == Verdict.DO_NOT_LAUNCH
    assert updated.risk_score == 8.3


def test_create_and_list_findings(runs: AuditRunRepository, findings: FindingRepository) -> None:
    run = runs.create(make_run())
    first = make_finding()
    second = make_finding(
        rule_id="DEBUG_MODE",
        severity=Severity.LOW,
        category=FindingCategory.CONFIG,
        title="Debug mode on",
    )

    created = findings.create_many(run.id, [first, second])

    assert [finding.id for finding in created] == [first.id, second.id]
    listed = findings.list_for_run(run.id)
    assert {finding.id for finding in listed} == {first.id, second.id}
    assert findings.list_for_run(uuid4()) == []


def test_finding_round_trip_keeps_json_fields(
    runs: AuditRunRepository, findings: FindingRepository
) -> None:
    run = runs.create(make_run())
    finding = make_finding(
        cwe="CWE-798",
        snippet="API_KEY = 'sk_live_****'",
        trace=[
            TraceStep(file="app.py", line=12, snippet="API_KEY = '...'", label="sink"),
        ],
        evidence=Evidence(secret_preview=SECRET_PREVIEW, notes="in config"),
        ai_verdict=AIVerdict(
            verdict=AIVerdictLabel.CONFIRMED,
            reason="A real key prefix.",
            quoted_code="API_KEY = '...'",
        ),
        fix_guidance="Move the key to the environment.",
    )

    created = findings.create(run.id, finding)
    stored = findings.get(finding.id)

    assert stored == created
    assert stored is not None
    assert stored.cwe == "CWE-798"
    assert stored.snippet == "API_KEY = 'sk_live_****'"
    assert stored.trace[0].label == "sink"
    assert stored.evidence.secret_preview == SECRET_PREVIEW
    assert stored.ai_verdict is not None
    assert stored.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert stored.fix_guidance == "Move the key to the environment."
    assert stored.status == FindingStatus.OPEN


def test_get_missing_finding_returns_none(findings: FindingRepository) -> None:
    assert findings.get(uuid4()) is None


def test_update_finding_status(runs: AuditRunRepository, findings: FindingRepository) -> None:
    run = runs.create(make_run())
    finding = findings.create(run.id, make_finding())

    updated = findings.update_status(finding.id, status=FindingStatus.FIXED)

    assert updated is not None
    assert updated.status == FindingStatus.FIXED
    assert findings.get(finding.id).status == FindingStatus.FIXED
    assert findings.update_status(uuid4(), status=FindingStatus.FIXED) is None


def test_get_finding_by_key(runs: AuditRunRepository, findings: FindingRepository) -> None:
    run = runs.create(make_run())
    finding = make_finding()
    findings.create(run.id, finding)

    assert findings.get_by_finding_key(run.id, "SECRET_GENERIC|app.py:12") == finding
    assert findings.get_by_finding_key(run.id, "SECRET_GENERIC|other.py:1") is None


def test_finding_key_for_code_finding() -> None:
    assert finding_key_for(make_finding()) == "SECRET_GENERIC|app.py:12"


def test_finding_key_for_journey_finding() -> None:
    finding = make_finding(
        engine=FindingEngine.JOURNEY,
        rule_id="JOURNEY_CHECKOUT_FAILS",
        file=None,
        start_line=None,
        end_line=None,
        evidence=Evidence(notes="Step: Check out"),
    )

    assert finding_key_for(finding) == "JOURNEY_CHECKOUT_FAILS|Check out"


def test_finding_key_for_live_finding() -> None:
    finding = make_finding(
        engine=FindingEngine.LIVE,
        rule_id="CORS_OPEN",
        file=None,
        start_line=None,
        end_line=None,
        evidence=Evidence(
            http=HttpEvidence(method="GET", url="https://shop.example.com/", status=200)
        ),
    )

    assert finding_key_for(finding) == "CORS_OPEN|https://shop.example.com/"


def test_run_id_type_is_uuid(runs: AuditRunRepository) -> None:
    run = runs.create(make_run())

    assert isinstance(run.id, UUID)
