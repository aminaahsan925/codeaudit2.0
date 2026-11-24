"""Owner access rules for audit runs.

An owned run (is_guest False) is visible only to the user who created it:
the run's stored owner must equal the signed-in principal's subject. A
guest run stays open by run id, since there is no guest identity system
to check against.
"""

from app.core.errors import NotFoundError, UnauthorizedError
from app.core.security import Principal
from app.schemas.audit_run import AuditRun


def require_run_owner(
    run: AuditRun,
    owner: str | None,
    principal: Principal | None,
    *,
    not_found_message: str = "Audit run not found.",
) -> None:
    """Allow the run's owner (or anyone, for a guest run); refuse the rest.

    No principal at all is a 401. A signed-in user who is not the owner
    gets a 404, identical to a missing run, so the run's existence stays
    hidden. The dev stub principal ("dev") only matches runs whose owner
    is "dev", never a real user's run, because the check is a plain
    subject-to-owner comparison. A run with no owner recorded admits
    nobody, which fails closed.
    """
    if run.is_guest:
        return
    if principal is None:
        raise UnauthorizedError("Missing or invalid bearer token.")
    if owner is None or principal.subject != owner:
        raise NotFoundError(not_found_message)
