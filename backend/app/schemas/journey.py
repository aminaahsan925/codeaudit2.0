"""Schemas for user-defined (custom) journeys.

A custom journey replaces the default sign up, log in, add to cart, check
out flow with steps the user defines: go to a URL, fill a field, click a
button, expect text on the page. The definition is stored on the run and
executed by the journey runner instead of the default steps.

Go-to URLs stay on the live site: a relative path resolves against the
live URL origin, and an absolute URL must share that origin (scheme, host
and port). Anything else is rejected at creation and fails the step at
run time, so a custom journey can never steer the browser elsewhere.
"""

from __future__ import annotations

import json
from enum import StrEnum
from urllib.parse import urlparse

from pydantic import BaseModel, Field, TypeAdapter, ValidationError, model_validator

MAX_CUSTOM_JOURNEY_STEPS = 20
MAX_JOURNEY_DEFINITION_CHARS = 32768


class JourneyStepAction(StrEnum):
    GOTO = "goto"
    FILL = "fill"
    CLICK = "click"
    EXPECT_TEXT = "expect_text"


class JourneyStepDefinition(BaseModel):
    """One user-defined journey step.

    Which fields apply depends on the action: goto needs `url`, fill needs
    `selector` and `value`, click needs `selector`, expect_text needs
    `text`. `name` is an optional label shown in the report; without one
    the runner derives a name from the action.
    """

    action: JourneyStepAction
    url: str | None = Field(default=None, max_length=2083)
    selector: str | None = Field(default=None, max_length=1024)
    value: str | None = Field(default=None, max_length=4096)
    text: str | None = Field(default=None, max_length=1024)
    name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _check_action_fields(self) -> JourneyStepDefinition:
        """Per-action required fields, with whitespace trimmed."""
        self.url = _stripped_or_none(self.url)
        self.selector = _stripped_or_none(self.selector)
        self.text = _stripped_or_none(self.text)
        self.name = _stripped_or_none(self.name)
        if self.action is JourneyStepAction.GOTO:
            if not self.url:
                raise ValueError("A go-to step needs a URL.")
            if self.url.startswith("//"):
                raise ValueError("A go-to URL must not be protocol-relative.")
            if not self.url.startswith("/"):
                parsed = urlparse(self.url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    raise ValueError("A go-to URL must be an http(s) URL or a path.")
        elif self.action is JourneyStepAction.FILL:
            if not self.selector:
                raise ValueError("A fill step needs a selector.")
            if self.value is None or self.value == "":
                raise ValueError("A fill step needs a value.")
        elif self.action is JourneyStepAction.CLICK:
            if not self.selector:
                raise ValueError("A click step needs a selector.")
        elif self.action is JourneyStepAction.EXPECT_TEXT and not self.text:
            raise ValueError("An expect-text step needs the text to expect.")
        return self


def _stripped_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _origin(url: str) -> tuple[str, str, int | None]:
    """The origin of a URL: scheme, host and port."""
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError:
        port = None
    return (parsed.scheme.lower(), (parsed.hostname or "").lower(), port)


def resolve_goto_url(base_url: str, url: str) -> str:
    """Resolve a go-to URL against the live URL origin.

    A relative path resolves against the base origin; an absolute URL must
    share the base origin. Raises ValueError for anything else, so the
    runner fails the step instead of navigating away from the live site.
    """
    if url.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{url}"
    if _origin(url) != _origin(base_url):
        raise ValueError(f"Go-to URL {url} leaves the live site.")
    return url


def _check_goto_same_origin(steps: list[JourneyStepDefinition], live_url: str) -> None:
    """Every absolute go-to URL must share the live URL origin."""
    base_origin = _origin(live_url)
    for step in steps:
        if step.action is not JourneyStepAction.GOTO or step.url is None:
            continue
        if step.url.startswith("/"):
            continue  # a relative path stays on the live site by construction
        if _origin(step.url) != base_origin:
            raise ValueError(f"Go-to URL {step.url} leaves the live site.")


def _first_validation_message(exc: ValidationError) -> str:
    """The first Pydantic error as 'Step N: <message>'."""
    error = exc.errors()[0]
    loc = error.get("loc", ())
    message = error.get("msg", "Invalid journey step.")
    if loc and isinstance(loc[0], int):
        return f"Step {loc[0] + 1}: {message}"
    return message


def parse_journey_definition(
    raw: str | None, live_url: str | None
) -> list[JourneyStepDefinition] | None:
    """Parse and validate a custom journey JSON payload.

    Returns None when no definition was supplied (or it is an empty list),
    so the default journey runs. Raises ValueError with a user-facing
    message when the JSON is malformed, a step is invalid, the step cap is
    exceeded, or a go-to URL leaves the live URL origin.
    """
    if raw is None or raw.strip() == "":
        return None
    if live_url is None:
        raise ValueError("A custom journey needs a live URL.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("The journey definition is not valid JSON.") from None
    if not isinstance(data, list):
        raise ValueError("The journey definition must be a list of steps.")
    if len(data) == 0:
        return None
    if len(data) > MAX_CUSTOM_JOURNEY_STEPS:
        raise ValueError(f"A custom journey has at most {MAX_CUSTOM_JOURNEY_STEPS} steps.")
    try:
        steps = TypeAdapter(list[JourneyStepDefinition]).validate_python(data)
    except ValidationError as exc:
        raise ValueError(_first_validation_message(exc)) from exc
    _check_goto_same_origin(steps, live_url)
    return steps
