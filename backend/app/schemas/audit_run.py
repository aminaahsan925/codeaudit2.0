"""AuditRun: one execution of the audit pipeline for a project.

Mirrors `docs/api-contract.md` (Domain schemas -> AuditRun).
"""

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, field_validator


class AuditRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Verdict(StrEnum):
    LAUNCH = "launch"
    FIX_FIRST = "fix_first"
    DO_NOT_LAUNCH = "do_not_launch"


class AuditRun(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: UUID
    project_name: str = Field(min_length=1, max_length=200)
    # http(s) only: rejects file:, javascript:, ssh: and scheme-less values.
    repo_url: HttpUrl | None = None
    live_url: HttpUrl | None = None
    status: AuditRunStatus = AuditRunStatus.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    verdict: Verdict | None = None
    risk_score: float | None = Field(default=None, ge=0.0, le=10.0)
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    error: str | None = None
    share_token: str | None = None
    is_guest: bool = False
    # Journey steps as stored JSON dicts (name, status, screenshot, error).
    # The matching ORM column lands on the audit-run branch; None until then.
    journey_steps: list[dict[str, Any]] | None = None

    @field_validator("risk_score")
    @classmethod
    def _one_decimal(cls, value: float | None) -> float | None:
        return None if value is None else round(value, 1)
