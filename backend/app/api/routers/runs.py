"""Audit run endpoints: create, read, list, rerun, artifacts.

POST /api/runs accepts guests (no auth) and owners (a valid bearer token
makes the run owned). The pipeline runs as a FastAPI BackgroundTask; the
response returns the run with status queued. Journey credentials are
passed to the background task in memory only and are never persisted.
Domain verification uses the server-issued token stored for the domain
and the run owner (see the verification router); no token is accepted
from the client.
"""

from __future__ import annotations

import re
import secrets
import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import HttpUrl

from app.api.deps import (
    CurrentPrincipal,
    DbSession,
    OptionalPrincipal,
    SettingsDep,
    bearer_scheme,
)
from app.core.errors import AppError, NotFoundError, UnauthorizedError
from app.core.ratelimit import enforce_audit_rate_limit
from app.repositories.audit_runs import AuditRunRepository
from app.schemas.audit_run import AuditRun
from app.schemas.error import error_responses
from app.schemas.journey import MAX_JOURNEY_DEFINITION_CHARS, parse_journey_definition
from app.schemas.run_create import RerunRequest
from app.services.runs import execute_run, validate_github_url

router = APIRouter(prefix="/runs", tags=["runs"])

_ARTIFACT_MEDIA_TYPES = {
    ".png": "image/png",
}

# Only journey screenshots are downloadable as artifacts. The stored
# upload zip (and anything else in the run dir) must never be served over
# HTTP: it holds the user's full source, including every secret the
# scanners carefully mask in findings. Reruns reuse the zip server-side.
_SCREENSHOT_NAME_RE = re.compile(r"step-\d{2}-[a-z0-9-]+\.png")


def _check_journey_credentials(journey_email: str | None, journey_password: str | None) -> None:
    """Journey credentials come as a pair, or not at all."""
    if bool(journey_email) != bool(journey_password):
        raise AppError("Provide both a journey email and password, or neither.")


def _rate_limit_token(
    principal: object | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    """The rate-limit key's token half: the bearer token when authenticated."""
    if principal is None or credentials is None:
        return None
    return credentials.credentials


@router.post(
    "",
    status_code=201,
    summary="Start an audit run",
    responses=error_responses(400, 401, 422, 429),
)
async def create_run(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    session: DbSession,
    principal: OptionalPrincipal,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    project_name: Annotated[str, Form(min_length=1, max_length=200)],
    repo_url: Annotated[HttpUrl | None, Form()] = None,
    live_url: Annotated[HttpUrl | None, Form()] = None,
    zip_file: Annotated[UploadFile | None, File()] = None,
    journey_email: Annotated[str | None, Form(max_length=320)] = None,
    journey_password: Annotated[str | None, Form(max_length=1024)] = None,
    journey_definition: Annotated[str | None, Form(max_length=MAX_JOURNEY_DEFINITION_CHARS)] = None,
) -> AuditRun:
    if repo_url is None and zip_file is None:
        raise AppError("Provide a GitHub repo URL or upload a zip file.")
    if repo_url is not None and validate_github_url(str(repo_url)) is None:
        raise AppError("The repo URL must be an https GitHub URL.")
    if zip_file is not None and not (zip_file.filename or "").lower().endswith(".zip"):
        raise AppError("The uploaded file must be a .zip file.")
    _check_journey_credentials(journey_email, journey_password)
    try:
        steps = parse_journey_definition(
            journey_definition, str(live_url) if live_url is not None else None
        )
    except ValueError as exc:
        raise AppError(str(exc)) from exc
    # Rate limit after validation, so bad requests do not consume quota.
    enforce_audit_rate_limit(request, settings, _rate_limit_token(principal, credentials))

    run_id = uuid4()
    run = AuditRun(
        id=run_id,
        project_name=project_name,
        repo_url=repo_url,
        live_url=live_url,
        share_token=secrets.token_urlsafe(32),
        is_guest=principal is None,
        journey_definition=steps,
    )
    created = AuditRunRepository(session).create(
        run, owner=principal.subject if principal is not None else None
    )
    session.commit()

    upload_path: Path | None = None
    if zip_file is not None:
        run_dir = settings.artifact_dir / str(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        upload_path = run_dir / "upload.zip"
        upload_path.write_bytes(await zip_file.read())

    background_tasks.add_task(
        execute_run,
        run_id,
        settings,
        None,
        upload_path=upload_path,
        journey_email=journey_email,
        journey_password=journey_password,
        owner=principal.subject if principal is not None else None,
    )
    return created


@router.get("", summary="List my audit runs", responses=error_responses(401))
def list_runs(principal: CurrentPrincipal, session: DbSession) -> list[AuditRun]:
    return AuditRunRepository(session).list_by_owner(principal.subject)


@router.get("/{run_id}", summary="Get an audit run", responses=error_responses(404))
def get_run(run_id: UUID, session: DbSession) -> AuditRun:
    run = AuditRunRepository(session).get(run_id)
    if run is None:
        raise NotFoundError("Audit run not found.")
    return run


@router.post(
    "/{run_id}/rerun",
    status_code=201,
    summary="Re-run an audit after fixes",
    responses=error_responses(400, 401, 404, 422, 429),
)
async def rerun_run(
    run_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    session: DbSession,
    principal: OptionalPrincipal,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    payload: RerunRequest | None = None,
) -> AuditRun:
    original = AuditRunRepository(session).get(run_id)
    if original is None:
        raise NotFoundError("Audit run not found.")
    if not original.is_guest and principal is None:
        raise UnauthorizedError("Missing or invalid bearer token.")
    rerun = payload or RerunRequest()
    _check_journey_credentials(rerun.journey_email, rerun.journey_password)
    enforce_audit_rate_limit(request, settings, _rate_limit_token(principal, credentials))

    new_id = uuid4()
    new_run = AuditRun(
        id=new_id,
        project_name=original.project_name,
        repo_url=original.repo_url,
        live_url=original.live_url,
        share_token=secrets.token_urlsafe(32),
        is_guest=original.is_guest,
        previous_run_id=original.id,
        # A rerun repeats the same journey as the original run.
        journey_definition=original.journey_definition,
    )
    owner = principal.subject if principal is not None and not original.is_guest else None
    created = AuditRunRepository(session).create(new_run, owner=owner)

    upload_path: Path | None = None
    if original.repo_url is None:
        # Zip rerun: re-use the stored upload. If it is gone, the pipeline
        # fails the new run with a safe message instead of scanning nothing.
        stored_zip = settings.artifact_dir / str(run_id) / "upload.zip"
        if stored_zip.is_file():
            run_dir = settings.artifact_dir / str(new_id)
            run_dir.mkdir(parents=True, exist_ok=True)
            upload_path = run_dir / "upload.zip"
            shutil.copyfile(stored_zip, upload_path)
    session.commit()

    background_tasks.add_task(
        execute_run,
        new_id,
        settings,
        None,
        upload_path=upload_path,
        journey_email=rerun.journey_email,
        journey_password=rerun.journey_password,
        owner=owner,
    )
    return created


@router.get(
    "/{run_id}/artifacts/{name}",
    summary="Get a run artifact",
    responses=error_responses(404),
)
def get_artifact(run_id: UUID, name: str, settings: SettingsDep) -> FileResponse:
    run_dir = settings.artifact_dir / str(run_id)
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise NotFoundError("Artifact not found.")
    if _SCREENSHOT_NAME_RE.fullmatch(name) is None:
        raise NotFoundError("Artifact not found.")
    path = (run_dir / name).resolve()
    if not path.is_relative_to(run_dir.resolve()) or not path.is_file():
        raise NotFoundError("Artifact not found.")
    media_type = _ARTIFACT_MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=media_type)
