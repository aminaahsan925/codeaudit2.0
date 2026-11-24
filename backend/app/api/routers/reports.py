"""Report routes: full report JSON, public share link, PDF export."""

import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import DbSession, OptionalPrincipal, SettingsDep, bearer_scheme
from app.api.run_access import require_run_owner
from app.core.config import Settings
from app.core.errors import NotFoundError, UnauthorizedError
from app.core.security import Principal, verify_bearer_token
from app.repositories.audit_runs import AuditRunRepository
from app.repositories.findings import FindingRepository
from app.schemas.audit_run import AuditRun
from app.schemas.error import error_responses
from app.schemas.report import ReportResponse
from app.services.report.pdf import render_report_pdf
from app.services.report.report import build_report

router = APIRouter(tags=["reports"])


def _previous_run_id(run: AuditRun) -> UUID | None:
    """The run this one reran, if any."""
    return run.previous_run_id


def _report_for_run(session: Session, run: AuditRun) -> ReportResponse:
    findings = FindingRepository(session).list_for_run(run.id)
    previous_run: AuditRun | None = None
    previous_findings: list | None = None
    previous_run_id = _previous_run_id(run)
    if previous_run_id is not None:
        previous_run = AuditRunRepository(session).get(previous_run_id)
        if previous_run is not None:
            previous_findings = FindingRepository(session).list_for_run(previous_run.id)
    return build_report(run, findings, run.journey_steps, previous_run, previous_findings)


def _load_run(session: Session, run_id: UUID) -> AuditRun:
    run = AuditRunRepository(session).get(run_id)
    if run is None:
        raise NotFoundError("Report not found.")
    return run


@router.get(
    "/runs/{run_id}/report",
    summary="Full report for a run",
    response_model=ReportResponse,
    responses=error_responses(401, 404),
)
def get_run_report(
    run_id: UUID, session: DbSession, principal: OptionalPrincipal
) -> ReportResponse:
    repository = AuditRunRepository(session)
    run = _load_run(session, run_id)
    require_run_owner(
        run, repository.get_owner(run_id), principal, not_found_message="Report not found."
    )
    return _report_for_run(session, run)


@router.get(
    "/reports/shared/{token}",
    summary="Full report by share token (public)",
    response_model=ReportResponse,
    responses=error_responses(404),
)
def get_shared_report(token: str, session: DbSession) -> ReportResponse:
    run = AuditRunRepository(session).get_by_share_token(token)
    if run is None:
        raise NotFoundError("Report not found.")
    return _report_for_run(session, run)


def _pdf_authorized(
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
    token: str | None,
    run: AuditRun,
    owner: str | None,
    principal: Principal | None,
) -> bool:
    """The run's owner, the bearer stub (non-production only), or a
    matching share token. A guest run's PDF still needs the stub or a
    share token, as before: the run id alone never opens it."""
    if (
        not run.is_guest
        and principal is not None
        and owner is not None
        and principal.subject == owner
    ):
        return True
    if not settings.is_production:
        presented = credentials.credentials if credentials is not None else None
        if verify_bearer_token(presented, settings.api_auth_token):
            return True
    if token is not None and run.share_token is not None:
        return hmac.compare_digest(token, run.share_token)
    return False


@router.get(
    "/runs/{run_id}/report.pdf",
    summary="Report PDF for a run",
    responses=error_responses(401, 404),
)
def get_run_report_pdf(
    run_id: UUID,
    session: DbSession,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    principal: OptionalPrincipal,
    token: Annotated[str | None, Query(description="Share token for public access")] = None,
) -> Response:
    run = _load_run(session, run_id)
    owner = AuditRunRepository(session).get_owner(run_id)
    if not _pdf_authorized(settings, credentials, token, run, owner, principal):
        raise UnauthorizedError("A valid bearer token or share token is required.")
    pdf = render_report_pdf(_report_for_run(session, run))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="launchaudit-report-{run_id}.pdf"'},
    )
