"""Finding assignment and tracking: validate a PATCH and persist it.

The router owns auth and the transaction; this module owns the rules:
unknown tracking statuses and over-long assignees are 400s, a finding
from another run is a 404, and only the fields present in the request
change (an empty assignee clears the assignment).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.repositories.findings import FindingRepository
from app.schemas.finding import (
    MAX_ASSIGNEE_LENGTH,
    Finding,
    FindingUpdate,
    TrackingStatus,
)

_TRACKING_VALUES = ", ".join(status.value for status in TrackingStatus)


def update_finding_assignment(
    session: Session,
    run_id: UUID,
    finding_id: UUID,
    payload: FindingUpdate,
) -> Finding:
    """Apply a partial assignment/status update. Commits nothing: the caller
    owns the transaction."""
    current = FindingRepository(session).get_for_run(run_id, finding_id)
    if current is None:
        raise NotFoundError("Finding not found.")

    assignee = current.assignee
    tracking_status = current.tracking_status
    if "assignee" in payload.model_fields_set:
        assignee = payload.assignee.strip() if payload.assignee is not None else None
        if assignee == "":
            assignee = None
        if assignee is not None and len(assignee) > MAX_ASSIGNEE_LENGTH:
            raise AppError(f"Assignee must be at most {MAX_ASSIGNEE_LENGTH} characters.")
    if "tracking_status" in payload.model_fields_set and payload.tracking_status is not None:
        try:
            tracking_status = TrackingStatus(payload.tracking_status)
        except ValueError:
            raise AppError(f"tracking_status must be one of: {_TRACKING_VALUES}.") from None

    updated = FindingRepository(session).update_assignment(
        finding_id, assignee=assignee, tracking_status=tracking_status
    )
    if updated is None:  # pragma: no cover - get_for_run just found it
        raise NotFoundError("Finding not found.")
    return updated
