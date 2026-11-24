"""Finding endpoints: assign a finding and track its fix.

PATCH /api/runs/{run_id}/findings/{finding_id} updates a finding's
assignee and tracking status. Auth follows the rerun rule: a guest run's
findings can be updated by anyone holding the link, an owned run's need
a valid bearer token.
"""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import DbSession, OptionalPrincipal
from app.core.errors import NotFoundError, UnauthorizedError
from app.repositories.audit_runs import AuditRunRepository
from app.schemas.error import error_responses
from app.schemas.finding import Finding, FindingUpdate
from app.services.findings import update_finding_assignment

router = APIRouter(prefix="/runs", tags=["findings"])


@router.patch(
    "/{run_id}/findings/{finding_id}",
    summary="Assign a finding and track its fix",
    response_model=Finding,
    responses=error_responses(400, 401, 404, 422),
)
def update_finding(
    run_id: UUID,
    finding_id: UUID,
    payload: FindingUpdate,
    session: DbSession,
    principal: OptionalPrincipal,
) -> Finding:
    run = AuditRunRepository(session).get(run_id)
    if run is None:
        raise NotFoundError("Audit run not found.")
    if not run.is_guest and principal is None:
        raise UnauthorizedError("Missing or invalid bearer token.")
    updated = update_finding_assignment(session, run_id, finding_id, payload)
    session.commit()
    return updated
