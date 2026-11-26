"""Database-backed rate limits for audit runs.

One limit for every caller: `settings.audit_rate_limit_per_hour` runs per
hour per key. The key identifies the caller the same way auth does (see
`app.api.deps.authenticate_optional`): a bearer session token first, then
the HttpOnly session cookie, both decoded with `verify_session_token`.
Signed-in callers are keyed by user id (`user:<id>`), so people sharing a
network each get their own limit; only true guests fall back to the
client IP (`ip:<address>`).

Counters live in the `rate_limit_counters` table, incremented with one
atomic upsert per attempt, so limits survive restarts and are shared by
every server instance using the same database. Windows are fixed: a
counter belongs to the current window and restarts when the window rolls
over. The limit value and the window size are unchanged from the old
in-memory limiter.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import RateLimitedError
from app.core.security import SESSION_COOKIE_NAME, Principal, verify_session_token
from app.models.rate_limit import RateLimitCounterModel

WINDOW_SECONDS = 3600


def _window_start(now: datetime) -> datetime:
    """Start of the fixed window containing `now`."""
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(epoch - (epoch % WINDOW_SECONDS), tz=UTC)


def _increment(session: Session, key: str, window_start: datetime) -> int:
    """Atomically add one hit for `key` in this window; return the new count.

    A single upsert statement does the work on Postgres and SQLite: insert
    a fresh counter, or, on key conflict, increment the existing counter
    when it belongs to this window and restart it when the window has
    rolled over. Other dialects fall back to a read-modify-write inside
    the transaction.
    """
    table = RateLimitCounterModel.__table__
    dialect = session.get_bind().dialect.name
    insert = {"postgresql": postgresql_insert, "sqlite": sqlite_insert}.get(dialect)
    if insert is not None:
        statement = insert(RateLimitCounterModel).values(
            key=key, window_start=window_start, count=1
        )
        statement = statement.on_conflict_do_update(
            index_elements=["key"],
            set_={
                "count": case(
                    (table.c.window_start == window_start, table.c.count + 1),
                    else_=1,
                ),
                "window_start": window_start,
            },
        )
        session.execute(statement)
        session.commit()
        count = session.execute(
            select(RateLimitCounterModel.count).where(RateLimitCounterModel.key == key)
        ).scalar_one()
        return int(count)

    row = session.get(RateLimitCounterModel, key)
    if row is None:
        session.add(RateLimitCounterModel(key=key, window_start=window_start, count=1))
        try:
            session.commit()
            return 1
        except IntegrityError:
            session.rollback()
            row = session.get(RateLimitCounterModel, key)
            if row is None:  # pragma: no cover - the conflicting row vanished
                raise
    if row.window_start != window_start:
        row.window_start = window_start
        row.count = 1
    else:
        row.count += 1
    session.commit()
    return int(row.count)


def check_and_record(session: Session, key: str, limit: int) -> bool:
    """Record a run attempt for `key`. True when allowed, False when over."""
    count = _increment(session, key, _window_start(datetime.now(UTC)))
    return count <= limit


def _user_id_from_request(request: Request, settings: Settings) -> UUID | None:
    """The signed-in user's id from the request, bearer token first, then
    the session cookie: the same order and the same decoding auth uses."""
    session_secret = settings.session_secret
    if session_secret is None:
        return None
    token: str | None = None
    authorization = request.headers.get("authorization")
    if authorization is not None and authorization.lower().startswith("bearer "):
        token = authorization[len("bearer ") :].strip() or None
    if token is None:
        token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    claims = verify_session_token(token, session_secret.get_secret_value())
    return claims.user_id if claims is not None else None


def rate_limit_key(
    request: Request,
    settings: Settings,
    principal: Principal | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    """Rate-limit key: `user:<id>` for signed-in callers, `token:<token>`
    for the development token stub, `ip:<address>` for true guests."""
    user_id = principal.user_id if principal is not None else None
    if user_id is None:
        user_id = _user_id_from_request(request, settings)
    if user_id is not None:
        return f"user:{user_id}"
    if principal is not None and credentials is not None:
        return f"token:{credentials.credentials}"
    host = request.client.host if request.client is not None else "unknown"
    return f"ip:{host}"


def enforce_audit_rate_limit(
    request: Request,
    settings: Settings,
    session: Session,
    principal: Principal | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    """Raise RateLimitedError when the caller has used up their hourly runs."""
    key = rate_limit_key(request, settings, principal, credentials)
    if not check_and_record(session, key, settings.audit_rate_limit_per_hour):
        raise RateLimitedError("Too many audit runs. Try again later.")


def reset(session: Session) -> None:
    """Clear all recorded hits (tests only)."""
    session.execute(delete(RateLimitCounterModel))
    session.commit()
