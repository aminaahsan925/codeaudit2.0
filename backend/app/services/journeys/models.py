"""Pydantic models for browser-driven user journeys."""

from enum import StrEnum

from pydantic import BaseModel, Field, SecretStr

from app.schemas.finding import Finding


class JourneyCredentials(BaseModel):
    """Test account the shop owner provides for the journey.

    The password is a SecretStr so it is never shown in logs or reprs.
    """

    email: str = Field(min_length=1)
    password: SecretStr


class JourneyStepStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class JourneyStep(BaseModel):
    """One step of a journey run: what happened, plus its screenshot."""

    name: str
    status: JourneyStepStatus
    screenshot: str | None = None
    error: str | None = None


class JourneyResult(BaseModel):
    """Outcome of a journey run: every step plus any findings.

    A passed journey has no findings. A failed journey has exactly one
    finding, for the first step that failed.
    """

    steps: list[JourneyStep] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
