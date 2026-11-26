"""Rate-limit counter ORM model: one row per caller key and window.

Counters live in the database (not process memory) so limits survive
restarts and are shared by every server instance using the same database.
`key` is `user:<id>` for signed-in callers, `token:<token>` for the
development token stub, or `ip:<address>` for guests. `window_start` is
the start of the current fixed window; when it no longer matches the
active window the count restarts from zero.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RateLimitCounterModel(Base):
    __tablename__ = "rate_limit_counters"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
