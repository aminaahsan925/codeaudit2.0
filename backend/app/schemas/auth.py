from pydantic import BaseModel


class MeResponse(BaseModel):
    """The authenticated principal."""

    subject: str
