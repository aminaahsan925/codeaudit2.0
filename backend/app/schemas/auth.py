from uuid import UUID

from pydantic import BaseModel


class UserResponse(BaseModel):
    """A signed-in user, as the frontend shows them."""

    id: UUID
    email: str
    name: str | None
    picture_url: str | None
    demo: bool


class MeResponse(BaseModel):
    """The authenticated principal.

    For a session sign-in the user fields are filled in; for the development
    token stub only `subject` is set (to "dev").
    """

    subject: str
    email: str | None = None
    name: str | None = None
    picture_url: str | None = None
    demo: bool = False


class ProvidersResponse(BaseModel):
    """Which sign-in options actually work right now."""

    google: bool
    demo: bool


class SessionResponse(BaseModel):
    """A fresh session: the user it belongs to.

    The token itself is never in the body; the backend sets it as an
    HttpOnly cookie on the response.
    """

    user: UserResponse
    demo: bool


class LogoutResponse(BaseModel):
    """Sign-out confirmation. The backend expires the session cookie."""

    signed_out: bool = True
