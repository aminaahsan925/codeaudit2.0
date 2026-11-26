"""Audit-run API tests: create, read, list, rerun, artifacts, rate limit.

The app is built with `create_app(...)` plus the runs router, and `get_db`
is overridden with a SQLite test session (the coordinator wires the router
into main.py at integration). The pipeline itself is stubbed here; the
real pipeline is covered by test_runs_runner.py.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routers import runs as runs_router
from app.core.config import Settings
from app.core.ratelimit import check_and_record
from app.core.ratelimit import reset as reset_rate_limits
from app.core.security import issue_session_token
from app.db import get_db
from app.main import create_app
from app.models import Base
from app.repositories.audit_runs import AuditRunRepository

SettingsFactory = Callable[..., Settings]

TEST_PASSWORD = "TestPass123"  # noqa: S105 - test-only journey password
TEST_DOMAIN_TOKEN = "verify-me"  # noqa: S105 - test-only domain token


def _zip_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _fresh_rate_limits(db_session: Session) -> Iterator[None]:
    reset_rate_limits(db_session)
    yield
    reset_rate_limits(db_session)


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
def make_runs_client(
    settings_factory: SettingsFactory, db_session: Session, tmp_path: Path
) -> Callable[..., TestClient]:
    def build(**overrides: Any) -> TestClient:
        settings = settings_factory(
            database_url=f"sqlite:///{tmp_path / 'test.db'}",
            artifact_dir=tmp_path / "artifacts",
            **overrides,
        )
        app = create_app(settings)
        app.include_router(runs_router.router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: db_session
        return TestClient(app, raise_server_exceptions=False)

    return build


@pytest.fixture
def client(make_runs_client: Callable[..., TestClient]) -> TestClient:
    return make_runs_client()


def _auth(api_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_token}"}


# ---------------------------------------------------------------- create


def test_create_guest_run_is_queued(
    client: TestClient, run_calls: list[dict[str, Any]], db_session: Session
) -> None:
    response = client.post(
        "/api/runs",
        data={
            "project_name": "Demo shop",
            "repo_url": "https://github.com/example/shop",
            "live_url": "https://shop.example.com",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["project_name"] == "Demo shop"
    assert body["status"] == "queued"
    assert body["progress"] == 0
    assert body["is_guest"] is True
    assert body["share_token"]
    assert body["previous_run_id"] is None
    assert body["domain_verified"] is False
    assert body["verdict"] is None
    assert body["risk_score"] is None

    assert len(run_calls) == 1
    assert run_calls[0]["run_id"] == UUID(body["id"])
    assert run_calls[0]["upload_path"] is None

    stored = AuditRunRepository(db_session).get(UUID(body["id"]))
    assert stored is not None
    assert stored.status.value == "queued"


def test_create_with_zip_saves_upload(
    client: TestClient, run_calls: list[dict[str, Any]], tmp_path: Path
) -> None:
    payload = _zip_bytes({"app.py": "print('hello')\n"})

    response = client.post(
        "/api/runs",
        data={"project_name": "Zip shop"},
        files={"zip_file": ("shop.zip", payload, "application/zip")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["repo_url"] is None
    upload = tmp_path / "artifacts" / body["id"] / "upload.zip"
    assert upload.is_file()
    assert upload.read_bytes() == payload
    assert run_calls[0]["upload_path"] == upload


def test_create_requires_a_code_source(client: TestClient) -> None:
    response = client.post("/api/runs", data={"project_name": "No code"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.parametrize(
    "repo_url",
    [
        "https://gitlab.com/example/shop",
        "http://github.com/example/shop",
        "https://github.com.evil.com/example/shop",
        "https://github.com/example",
    ],
)
def test_create_rejects_non_github_repo_url(client: TestClient, repo_url: str) -> None:
    response = client.post("/api/runs", data={"project_name": "Shop", "repo_url": repo_url})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_create_rejects_non_zip_file(client: TestClient) -> None:
    response = client.post(
        "/api/runs",
        data={"project_name": "Shop"},
        files={"zip_file": ("shop.txt", b"not a zip", "text/plain")},
    )

    assert response.status_code == 400


def test_create_requires_project_name(client: TestClient) -> None:
    response = client.post("/api/runs", data={"repo_url": "https://github.com/example/shop"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_rejects_partial_journey_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/runs",
        data={
            "project_name": "Shop",
            "repo_url": "https://github.com/example/shop",
            "journey_email": "tester@example.com",
        },
    )

    assert response.status_code == 400


def test_create_with_valid_token_is_owned(
    client: TestClient, api_token: str, run_calls: list[dict[str, Any]]
) -> None:
    response = client.post(
        "/api/runs",
        data={"project_name": "Owned", "repo_url": "https://github.com/example/shop"},
        headers=_auth(api_token),
    )

    assert response.status_code == 201
    assert response.json()["is_guest"] is False
    assert len(run_calls) == 1


def test_create_with_invalid_token_is_401(client: TestClient) -> None:
    response = client.post(
        "/api/runs",
        data={"project_name": "Shop", "repo_url": "https://github.com/example/shop"},
        headers={"Authorization": "Bearer wrong"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


# ------------------------------------------------------------- rate limit


def test_rate_limit_returns_429(
    make_runs_client: Callable[..., TestClient],
) -> None:
    client = make_runs_client(audit_rate_limit_per_hour=2)
    payload = {"project_name": "Shop", "repo_url": "https://github.com/example/shop"}

    assert client.post("/api/runs", data=payload).status_code == 201
    assert client.post("/api/runs", data=payload).status_code == 201
    response = client.post("/api/runs", data=payload)

    assert response.status_code == 429
    assert response.json() == {
        "error": {"code": "rate_limited", "message": "Too many audit runs. Try again later."}
    }


def test_rate_limit_is_per_key(db_session: Session) -> None:
    assert check_and_record(db_session, "ip:1.2.3.4", 1) is True
    assert check_and_record(db_session, "ip:1.2.3.4", 1) is False
    assert check_and_record(db_session, "ip:5.6.7.8", 1) is True
    reset_rate_limits(db_session)
    assert check_and_record(db_session, "ip:1.2.3.4", 1) is True


def test_rate_limit_counters_are_shared_across_sessions(db_session: Session) -> None:
    """Two sessions on one database (two server instances, or one instance
    after a restart) agree on the count: the limit lives in the database,
    not in process memory."""
    maker = sessionmaker(bind=db_session.get_bind(), autoflush=False, expire_on_commit=False)
    with maker() as other_session:
        assert check_and_record(db_session, "user:shared", 2) is True
        assert check_and_record(other_session, "user:shared", 2) is True
        assert check_and_record(db_session, "user:shared", 2) is False


def test_cookie_session_user_has_own_rate_limit_bucket(
    make_runs_client: Callable[..., TestClient],
) -> None:
    """A signed-in user (session cookie) is limited by user id, not by the
    shared client IP: exhausting their bucket does not limit a guest from
    the same address, and vice versa."""
    secret = "test-session-secret-for-rate-limit-tests"  # noqa: S105 - test value
    client = make_runs_client(audit_rate_limit_per_hour=1, session_secret=secret)
    token = issue_session_token(
        secret,
        user_id=uuid4(),
        email="owner@example.com",
        name="Owner",
        picture_url=None,
        demo=False,
    )
    payload = {"project_name": "Shop", "repo_url": "https://github.com/example/shop"}
    cookies = {"launchaudit_session": token}

    assert client.post("/api/runs", data=payload, cookies=cookies).status_code == 201
    response = client.post("/api/runs", data=payload, cookies=cookies)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"

    # Same client IP, no cookie: the guest bucket is untouched.
    assert client.post("/api/runs", data=payload).status_code == 201


def test_rate_limit_applies_to_rerun(make_runs_client: Callable[..., TestClient]) -> None:
    client = make_runs_client(audit_rate_limit_per_hour=1)
    created = client.post(
        "/api/runs",
        data={"project_name": "Shop", "repo_url": "https://github.com/example/shop"},
    )
    assert created.status_code == 201

    response = client.post(f"/api/runs/{created.json()['id']}/rerun", json={})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


# ------------------------------------------------------------------- read


def test_get_run_by_id(client: TestClient) -> None:
    created = client.post(
        "/api/runs",
        data={"project_name": "Shop", "repo_url": "https://github.com/example/shop"},
    )
    run_id = created.json()["id"]

    response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["id"] == run_id


def test_get_missing_run_is_404(client: TestClient) -> None:
    response = client.get(f"/api/runs/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_list_runs_requires_auth(client: TestClient) -> None:
    response = client.get("/api/runs")

    assert response.status_code == 401


def test_list_runs_returns_owned_newest_first(
    client: TestClient, api_token: str, db_session: Session
) -> None:
    # A guest run must not appear in the owner's list.
    client.post(
        "/api/runs",
        data={"project_name": "Guest", "repo_url": "https://github.com/example/guest"},
    )
    first = client.post(
        "/api/runs",
        data={"project_name": "First", "repo_url": "https://github.com/example/first"},
        headers=_auth(api_token),
    ).json()
    second = client.post(
        "/api/runs",
        data={"project_name": "Second", "repo_url": "https://github.com/example/second"},
        headers=_auth(api_token),
    ).json()

    runs = AuditRunRepository(db_session)
    runs.update_status(UUID(first["id"]), started_at=datetime(2026, 11, 24, 1, 0, tzinfo=UTC))
    runs.update_status(UUID(second["id"]), started_at=datetime(2026, 11, 24, 2, 0, tzinfo=UTC))
    db_session.commit()

    response = client.get("/api/runs", headers=_auth(api_token))

    assert response.status_code == 200
    assert [run["project_name"] for run in response.json()] == ["Second", "First"]


# ------------------------------------------------------------------ rerun


def test_rerun_copies_inputs_and_links_previous(
    client: TestClient, run_calls: list[dict[str, Any]]
) -> None:
    original = client.post(
        "/api/runs",
        data={
            "project_name": "Shop",
            "repo_url": "https://github.com/example/shop",
            "live_url": "https://shop.example.com",
        },
    ).json()

    response = client.post(
        f"/api/runs/{original['id']}/rerun",
        json={
            "journey_email": "tester@example.com",
            "journey_password": TEST_PASSWORD,
            "domain_token": TEST_DOMAIN_TOKEN,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] != original["id"]
    assert body["previous_run_id"] == original["id"]
    assert body["project_name"] == "Shop"
    assert body["repo_url"] == "https://github.com/example/shop"
    # HttpUrl normalizes a bare host with a trailing slash.
    assert body["live_url"] == "https://shop.example.com/"
    assert body["status"] == "queued"
    assert body["is_guest"] is True
    assert body["share_token"] != original["share_token"]

    rerun_call = run_calls[1]
    assert rerun_call["run_id"] == UUID(body["id"])
    assert rerun_call["journey_email"] == "tester@example.com"
    assert rerun_call["journey_password"] == TEST_PASSWORD
    assert rerun_call["domain_token"] == TEST_DOMAIN_TOKEN


def test_rerun_of_owned_run_requires_auth(client: TestClient, api_token: str) -> None:
    original = client.post(
        "/api/runs",
        data={"project_name": "Owned", "repo_url": "https://github.com/example/shop"},
        headers=_auth(api_token),
    ).json()

    assert client.post(f"/api/runs/{original['id']}/rerun", json={}).status_code == 401
    rerun = client.post(f"/api/runs/{original['id']}/rerun", json={}, headers=_auth(api_token))
    assert rerun.status_code == 201
    assert rerun.json()["is_guest"] is False


def test_rerun_missing_run_is_404(client: TestClient) -> None:
    response = client.post(f"/api/runs/{uuid4()}/rerun", json={})

    assert response.status_code == 404


def test_rerun_reuses_stored_zip(
    client: TestClient, run_calls: list[dict[str, Any]], tmp_path: Path
) -> None:
    payload = _zip_bytes({"app.py": "print('hello')\n"})
    original = client.post(
        "/api/runs",
        data={"project_name": "Zip shop"},
        files={"zip_file": ("shop.zip", payload, "application/zip")},
    ).json()

    response = client.post(f"/api/runs/{original['id']}/rerun", json={})

    assert response.status_code == 201
    rerun_id = response.json()["id"]
    copied = tmp_path / "artifacts" / rerun_id / "upload.zip"
    assert copied.is_file()
    assert copied.read_bytes() == payload
    assert run_calls[1]["upload_path"] == copied


def test_rerun_rejects_partial_journey_credentials(client: TestClient) -> None:
    original = client.post(
        "/api/runs",
        data={"project_name": "Shop", "repo_url": "https://github.com/example/shop"},
    ).json()

    response = client.post(
        f"/api/runs/{original['id']}/rerun",
        json={"journey_email": "tester@example.com"},
    )

    assert response.status_code == 400


# --------------------------------------------------------------- artifacts


def test_artifact_serving(client: TestClient, tmp_path: Path) -> None:
    run_id = client.post(
        "/api/runs",
        data={"project_name": "Shop", "repo_url": "https://github.com/example/shop"},
    ).json()["id"]
    artifact_dir = tmp_path / "artifacts" / run_id
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "step-04-checkout.png").write_bytes(b"\x89PNG fake image")
    (artifact_dir / "report.pdf").write_bytes(b"%PDF fake pdf")
    (artifact_dir / "upload.zip").write_bytes(b"PK fake zip")

    png = client.get(f"/api/runs/{run_id}/artifacts/step-04-checkout.png")
    assert png.status_code == 200
    assert png.headers["content-type"] == "image/png"
    assert png.content == b"\x89PNG fake image"

    # Only journey screenshots are downloadable: the stored upload zip
    # holds the user's full source (including masked secrets) and must
    # never be served, and PDFs have their own endpoint.
    pdf = client.get(f"/api/runs/{run_id}/artifacts/report.pdf")
    assert pdf.status_code == 404
    assert pdf.json()["error"]["code"] == "not_found"
    zipped = client.get(f"/api/runs/{run_id}/artifacts/upload.zip")
    assert zipped.status_code == 404
    assert zipped.json()["error"]["code"] == "not_found"


def test_artifact_missing_is_404(client: TestClient) -> None:
    run_id = client.post(
        "/api/runs",
        data={"project_name": "Shop", "repo_url": "https://github.com/example/shop"},
    ).json()["id"]

    response = client.get(f"/api/runs/{run_id}/artifacts/nope.png")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_artifact_traversal_is_rejected(client: TestClient, tmp_path: Path) -> None:
    run_id = client.post(
        "/api/runs",
        data={"project_name": "Shop"},
        files={"zip_file": ("shop.zip", _zip_bytes({"a.py": "x = 1\n"}), "application/zip")},
    ).json()["id"]

    # Backslash traversal: the name reaches the endpoint and must be refused.
    response = client.get(f"/api/runs/{run_id}/artifacts/..%5Cupload.zip")
    assert response.status_code == 404

    # Encoded slash traversal: must never escape the run directory.
    response = client.get(f"/api/runs/{run_id}/artifacts/..%2Fupload.zip")
    assert response.status_code == 404
    assert (tmp_path / "artifacts" / run_id / "upload.zip").is_file()
