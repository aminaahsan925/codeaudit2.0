from fastapi import APIRouter

from app.api.deps import SettingsDep
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
def health(settings: SettingsDep) -> HealthResponse:
    """Public liveness probe. Does not touch the database."""
    return HealthResponse(status="ok", version=settings.app_version)
