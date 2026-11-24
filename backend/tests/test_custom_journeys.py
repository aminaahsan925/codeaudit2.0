"""Custom journey tests: step validation, runner execution, persistence.

The runner tests drive a tiny local HTTP server (a password reset flow)
in a background thread, so no external demo app is needed. The server is
bound to 127.0.0.1 on an ephemeral port with loopback checks enabled.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routers import runs as runs_router
from app.core.config import Settings
from app.core.ratelimit import reset as reset_rate_limits
from app.db import get_db
from app.main import create_app
from app.models import Base
from app.repositories.audit_runs import AuditRunRepository
from app.schemas.audit_run import AuditRun
from app.schemas.journey import (
    MAX_CUSTOM_JOURNEY_STEPS,
    JourneyStepAction,
    JourneyStepDefinition,
    parse_journey_definition,
)
from app.services.journeys import JourneyCredentials, JourneyStepStatus, run_journey

SettingsFactory = Callable[..., Settings]

LIVE_URL = "https://shop.example.com"

# Test-only password for the throwaway journey account; not a real secret.
TEST_PASSWORD = "TestPass123"  # noqa: S105

RESET_JOURNEY = [
    {"action": "goto", "url": "/reset", "name": "Open reset page"},
    {"action": "fill", "selector": "#email", "value": "user@example.com"},
    {"action": "click", "selector": 'button[type="submit"]'},
    {"action": "expect_text", "text": "Check your email"},
]


# ------------------------------------------------------------------ parsing


def test_parse_valid_definition() -> None:
    steps = parse_journey_definition(json.dumps(RESET_JOURNEY), LIVE_URL)

    assert steps is not None
    assert [step.action for step in steps] == [
        JourneyStepAction.GOTO,
        JourneyStepAction.FILL,
        JourneyStepAction.CLICK,
        JourneyStepAction.EXPECT_TEXT,
    ]
    assert steps[0].name == "Open reset page"
    assert steps[1].selector == "#email"
    assert steps[1].value == "user@example.com"


def test_parse_empty_definition_returns_none() -> None:
    assert parse_journey_definition(None, LIVE_URL) is None
    assert parse_journey_definition("", LIVE_URL) is None
    assert parse_journey_definition("  ", LIVE_URL) is None
    assert parse_journey_definition("[]", LIVE_URL) is None


def test_parse_rejects_bad_json() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_journey_definition("{not json", LIVE_URL)


def test_parse_rejects_non_list_json() -> None:
    with pytest.raises(ValueError, match="must be a list of steps"):
        parse_journey_definition('{"action": "goto"}', LIVE_URL)


def test_parse_rejects_bad_action() -> None:
    with pytest.raises(ValueError, match="Step 1"):
        parse_journey_definition(json.dumps([{"action": "teleport", "url": "/reset"}]), LIVE_URL)


def test_parse_rejects_fill_without_selector_or_value() -> None:
    with pytest.raises(ValueError, match="Step 1: A fill step needs a selector"):
        parse_journey_definition(json.dumps([{"action": "fill", "value": "x"}]), LIVE_URL)
    with pytest.raises(ValueError, match="Step 1: A fill step needs a value"):
        parse_journey_definition(json.dumps([{"action": "fill", "selector": "#email"}]), LIVE_URL)


def test_parse_rejects_click_without_selector() -> None:
    with pytest.raises(ValueError, match="Step 2: A click step needs a selector"):
        parse_journey_definition(
            json.dumps(
                [
                    {"action": "goto", "url": "/reset"},
                    {"action": "click"},
                ]
            ),
            LIVE_URL,
        )


def test_parse_rejects_expect_text_without_text() -> None:
    with pytest.raises(ValueError, match="An expect-text step needs the text"):
        parse_journey_definition(json.dumps([{"action": "expect_text"}]), LIVE_URL)


def test_parse_rejects_non_http_goto_url() -> None:
    with pytest.raises(ValueError, match="must be an http\\(s\\) URL or a path"):
        parse_journey_definition(
            json.dumps([{"action": "goto", "url": "javascript:alert(1)"}]), LIVE_URL
        )


def test_parse_rejects_protocol_relative_goto_url() -> None:
    with pytest.raises(ValueError, match="must not be protocol-relative"):
        parse_journey_definition(
            json.dumps([{"action": "goto", "url": "//evil.example.com/x"}]), LIVE_URL
        )


def test_parse_rejects_step_cap_overflow() -> None:
    steps = [{"action": "goto", "url": "/reset"}] * (MAX_CUSTOM_JOURNEY_STEPS + 1)
    with pytest.raises(ValueError, match="at most 20 steps"):
        parse_journey_definition(json.dumps(steps), LIVE_URL)


def test_parse_accepts_exactly_the_step_cap() -> None:
    steps = [{"action": "goto", "url": "/reset"}] * MAX_CUSTOM_JOURNEY_STEPS
    parsed = parse_journey_definition(json.dumps(steps), LIVE_URL)
    assert parsed is not None
    assert len(parsed) == MAX_CUSTOM_JOURNEY_STEPS


def test_parse_rejects_off_origin_goto_url() -> None:
    with pytest.raises(ValueError, match="leaves the live site"):
        parse_journey_definition(
            json.dumps([{"action": "goto", "url": "https://other.example.com/"}]),
            LIVE_URL,
        )


def test_parse_rejects_different_port_and_scheme() -> None:
    with pytest.raises(ValueError, match="leaves the live site"):
        parse_journey_definition(
            json.dumps([{"action": "goto", "url": "https://shop.example.com:8443/"}]),
            LIVE_URL,
        )
    with pytest.raises(ValueError, match="leaves the live site"):
        parse_journey_definition(
            json.dumps([{"action": "goto", "url": "http://shop.example.com/"}]),
            LIVE_URL,
        )


def test_parse_accepts_same_origin_absolute_url() -> None:
    steps = parse_journey_definition(
        json.dumps([{"action": "goto", "url": "https://shop.example.com/reset"}]),
        LIVE_URL,
    )
    assert steps is not None
    assert steps[0].url == "https://shop.example.com/reset"


def test_parse_rejects_definition_without_live_url() -> None:
    with pytest.raises(ValueError, match="needs a live URL"):
        parse_journey_definition(json.dumps(RESET_JOURNEY), None)


# --------------------------------------------------------------- persistence


@pytest.fixture
def db_session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with maker() as session:
        yield session
    engine.dispose()


def test_journey_definition_round_trips_through_repository(db_session: Session) -> None:
    definition = [
        JourneyStepDefinition(action=JourneyStepAction.GOTO, url="/reset"),
        JourneyStepDefinition(action=JourneyStepAction.EXPECT_TEXT, text="Check your email"),
    ]
    run = AuditRun(
        id=uuid4(),
        project_name="Demo shop",
        live_url="https://shop.example.com",
        journey_definition=definition,
    )
    AuditRunRepository(db_session).create(run)
    db_session.commit()

    stored = AuditRunRepository(db_session).get(run.id)

    assert stored is not None
    assert stored.journey_definition == definition


def test_run_without_definition_round_trips_as_none(db_session: Session) -> None:
    run = AuditRun(id=uuid4(), project_name="Demo shop")
    AuditRunRepository(db_session).create(run)
    db_session.commit()

    stored = AuditRunRepository(db_session).get(run.id)

    assert stored is not None
    assert stored.journey_definition is None


# ---------------------------------------------------------------------- API


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> Iterator[None]:
    reset_rate_limits()
    yield
    reset_rate_limits()


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
    )
    app = create_app(settings)
    app.include_router(runs_router.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app, raise_server_exceptions=False)


def _create_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "project_name": "Demo shop",
        "repo_url": "https://github.com/example/shop",
        "live_url": LIVE_URL,
    }
    payload.update(overrides)
    return payload


def test_create_run_with_custom_journey_returns_and_persists_it(
    client: TestClient, run_calls: list[dict[str, Any]], db_session: Session
) -> None:
    response = client.post(
        "/api/runs",
        data=_create_payload(journey_definition=json.dumps(RESET_JOURNEY)),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["journey_definition"] == [
        {
            "action": "goto",
            "url": "/reset",
            "selector": None,
            "value": None,
            "text": None,
            "name": "Open reset page",
        },
        {
            "action": "fill",
            "url": None,
            "selector": "#email",
            "value": "user@example.com",
            "text": None,
            "name": None,
        },
        {
            "action": "click",
            "url": None,
            "selector": 'button[type="submit"]',
            "value": None,
            "text": None,
            "name": None,
        },
        {
            "action": "expect_text",
            "url": None,
            "selector": None,
            "value": None,
            "text": "Check your email",
            "name": None,
        },
    ]
    assert len(run_calls) == 1

    stored = AuditRunRepository(db_session).get(UUID(body["id"]))
    assert stored is not None
    assert stored.journey_definition is not None
    assert [step.action for step in stored.journey_definition] == [
        JourneyStepAction.GOTO,
        JourneyStepAction.FILL,
        JourneyStepAction.CLICK,
        JourneyStepAction.EXPECT_TEXT,
    ]


def test_create_run_without_journey_definition_returns_none(
    client: TestClient, run_calls: list[dict[str, Any]]
) -> None:
    response = client.post("/api/runs", data=_create_payload())

    assert response.status_code == 201
    assert response.json()["journey_definition"] is None


def test_create_run_rejects_off_origin_journey(client: TestClient) -> None:
    response = client.post(
        "/api/runs",
        data=_create_payload(
            journey_definition=json.dumps([{"action": "goto", "url": "https://other.example.com/"}])
        ),
    )

    assert response.status_code == 400
    assert "leaves the live site" in response.json()["error"]["message"]


def test_create_run_rejects_invalid_journey_step(client: TestClient) -> None:
    response = client.post(
        "/api/runs",
        data=_create_payload(journey_definition=json.dumps([{"action": "fill", "value": "x"}])),
    )

    assert response.status_code == 400
    assert "Step 1: A fill step needs a selector" in response.json()["error"]["message"]


def test_create_run_rejects_journey_without_live_url(client: TestClient) -> None:
    payload = _create_payload(journey_definition=json.dumps(RESET_JOURNEY))
    del payload["live_url"]
    response = client.post("/api/runs", data=payload)

    assert response.status_code == 400
    assert "needs a live URL" in response.json()["error"]["message"]


def test_rerun_copies_the_custom_journey(
    client: TestClient, run_calls: list[dict[str, Any]]
) -> None:
    created = client.post(
        "/api/runs",
        data=_create_payload(journey_definition=json.dumps(RESET_JOURNEY)),
    )
    assert created.status_code == 201
    original_id = created.json()["id"]

    response = client.post(f"/api/runs/{original_id}/rerun")

    assert response.status_code == 201
    body = response.json()
    assert body["journey_definition"] == created.json()["journey_definition"]
    assert body["previous_run_id"] == original_id


# -------------------------------------------------------------------- runner


RESET_FORM_HTML = """<!doctype html><html><body>
<h1>Reset your password</h1>
<form method="post" action="/reset">
<label for="email">Email</label>
<input id="email" name="email" type="email">
<button type="submit">Send reset link</button>
</form>
</body></html>"""

RESET_SENT_HTML = """<!doctype html><html><body>
<h1>Check your email</h1>
<p>Check your email for a reset link.</p>
</body></html>"""

HOME_HTML = """<!doctype html><html><body>
<h1>Demo shop</h1>
<a href="/reset">Forgot password?</a>
</body></html>"""


class _ResetAppHandler(BaseHTTPRequestHandler):
    """A minimal password-reset flow: home, reset form, reset sent."""

    def do_GET(self) -> None:
        if self.path == "/":
            self._send(HOME_HTML)
        elif self.path == "/reset":
            self._send(RESET_FORM_HTML)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path == "/reset":
            self._send(RESET_SENT_HTML)
        else:
            self.send_response(404)
            self.end_headers()

    def _send(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture(scope="module")
def reset_app_url() -> Iterator[str]:
    """Serve the reset-flow app on an ephemeral localhost port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ResetAppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _credentials() -> JourneyCredentials:
    return JourneyCredentials(email="journey@launchaudit.local", password=TEST_PASSWORD)


def test_custom_journey_passes_against_reset_flow(
    reset_app_url: str,
    settings_factory: SettingsFactory,
    tmp_path: Path,
) -> None:
    settings = settings_factory(allow_loopback_live_checks=True)
    artifact_dir = tmp_path / "custom-artifacts"

    result = run_journey(
        reset_app_url, _credentials(), artifact_dir, settings, journey_definition=RESET_JOURNEY
    )

    assert [step.name for step in result.steps] == [
        "Open reset page",
        "Fill #email",
        'Click button[type="submit"]',
        "Expect text 'Check your email'",
    ]
    assert [step.status for step in result.steps] == [JourneyStepStatus.PASSED] * 4
    assert [step.error for step in result.steps] == [None] * 4
    assert result.findings == []
    for filename in (
        "step-01-open-reset-page.png",
        "step-02-fill-email.png",
        "step-03-click-button-type-submit.png",
        "step-04-expect-text-check-your-email.png",
    ):
        assert (artifact_dir / filename).is_file()


def test_custom_journey_failure_skips_later_steps_and_makes_one_finding(
    reset_app_url: str,
    settings_factory: SettingsFactory,
    tmp_path: Path,
) -> None:
    settings = settings_factory(allow_loopback_live_checks=True)
    artifact_dir = tmp_path / "failing-artifacts"
    definition = [
        {"action": "goto", "url": "/reset"},
        {"action": "expect_text", "text": "No such text here"},
        {"action": "click", "selector": "#missing"},
    ]

    result = run_journey(
        reset_app_url, _credentials(), artifact_dir, settings, journey_definition=definition
    )

    assert [step.status for step in result.steps] == [
        JourneyStepStatus.PASSED,
        JourneyStepStatus.FAILED,
        JourneyStepStatus.SKIPPED,
    ]
    assert result.steps[1].error is not None
    assert "No such text here" in result.steps[1].error
    assert result.steps[2].error is not None
    assert "earlier step failed" in result.steps[2].error

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity.value == "high"
    assert finding.engine.value == "journey"
    assert finding.evidence.screenshot_url == "step-02-expect-text-no-such-text-here.png"
    assert finding.fix_guidance is not None
    assert "Why it matters" in finding.fix_guidance
    assert "How to fix" in finding.fix_guidance
    assert (artifact_dir / "step-02-expect-text-no-such-text-here.png").is_file()


def test_custom_journey_off_origin_goto_fails_the_step(
    reset_app_url: str,
    settings_factory: SettingsFactory,
    tmp_path: Path,
) -> None:
    settings = settings_factory(allow_loopback_live_checks=True)
    artifact_dir = tmp_path / "off-origin-artifacts"
    definition = [{"action": "goto", "url": "https://example.com/"}]

    result = run_journey(
        reset_app_url, _credentials(), artifact_dir, settings, journey_definition=definition
    )

    assert len(result.steps) == 1
    assert result.steps[0].status == JourneyStepStatus.FAILED
    assert result.steps[0].error is not None
    assert "leaves the live site" in result.steps[0].error
    assert len(result.findings) == 1


def test_default_journey_unchanged_without_definition(
    reset_app_url: str,
    settings_factory: SettingsFactory,
    tmp_path: Path,
) -> None:
    """No definition means the default four steps, not an empty journey.

    The reset-flow app has no sign up page, so the default journey fails
    at the first step; the point here is the plan, not the outcome.
    """
    settings = settings_factory(allow_loopback_live_checks=True)
    artifact_dir = tmp_path / "default-artifacts"

    result = run_journey(reset_app_url, _credentials(), artifact_dir, settings)

    assert [step.name for step in result.steps] == [
        "Sign up",
        "Log in",
        "Add to cart",
        "Check out",
    ]
    assert result.steps[0].status == JourneyStepStatus.FAILED
    assert result.steps[0].screenshot == "step-01-signup.png"
    assert (artifact_dir / "step-01-signup.png").is_file()


def test_invalid_stored_definition_raises(
    reset_app_url: str,
    settings_factory: SettingsFactory,
    tmp_path: Path,
) -> None:
    settings = settings_factory(allow_loopback_live_checks=True)
    with pytest.raises(ValueError, match="invalid"):
        run_journey(
            reset_app_url,
            _credentials(),
            tmp_path / "artifacts",
            settings,
            journey_definition=[{"action": "teleport"}],
        )
