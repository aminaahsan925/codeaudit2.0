from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.schemas.auth import MeResponse
from app.schemas.error import error_responses

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", summary="Current principal", responses=error_responses(401))
def me(principal: CurrentPrincipal) -> MeResponse:
    return MeResponse(subject=principal.subject)
