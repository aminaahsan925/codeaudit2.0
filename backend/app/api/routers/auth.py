"""Auth endpoints: Google sign-in, demo sign-in, session info.

Google sign-in is the OAuth2 code flow: login redirects to Google, the
callback swaps the code for an ID token, verifies it, and issues a session
token. Demo sign-in exists only while Google is unconfigured, so judges can
try the app without a Google account; it is labelled demo everywhere and is
never presented as Google sign-in.

Sessions travel as an HttpOnly cookie, never in a URL or in JavaScript
storage, so a token cannot leak into browser history, logs or Referer
headers and an XSS anywhere in the app cannot steal it.

The Google callback is a browser navigation, not an API call, so its
failures must never surface as a raw JSON error page: any failure or
cancellation sends the browser back to the frontend sign-in page with an
`error=google_failed` flag the page can show.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentPrincipal, DbSession, HttpClient, SettingsDep
from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.security import (
    clear_session_cookie,
    issue_oauth_state,
    issue_session_token,
    set_session_cookie,
    verify_oauth_state,
)
from app.schemas.auth import (
    LogoutResponse,
    MeResponse,
    ProvidersResponse,
    SessionResponse,
    UserResponse,
)
from app.schemas.error import error_responses
from app.schemas.user import User
from app.services.auth import (
    build_authorization_url,
    exchange_code,
    get_or_create_demo_user,
    upsert_google_user,
    verify_id_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _sign_in_failed(settings: Settings) -> RedirectResponse:
    """Send the browser back to the frontend sign-in page after a failed or
    cancelled Google sign-in, instead of showing a raw API error page."""
    return RedirectResponse(
        f"{settings.frontend_url}/sign-in?error=google_failed", status_code=302
    )


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        demo=user.is_demo,
    )


@router.get("/providers", summary="Available sign-in providers")
def providers(settings: SettingsDep) -> ProvidersResponse:
    """Which sign-in options actually work: Google when it is configured,
    demo sign-in only while Google is not."""
    google = settings.google_configured and settings.sessions_available
    demo = not settings.google_configured and settings.sessions_available
    return ProvidersResponse(google=google, demo=demo)


@router.get(
    "/google/login",
    summary="Start Google sign-in",
    responses=error_responses(404),
    response_class=RedirectResponse,
)
def google_login(settings: SettingsDep) -> RedirectResponse:
    """Redirect the browser to Google's sign-in page."""
    session_secret = settings.session_secret
    if not settings.google_configured or session_secret is None:
        raise NotFoundError("Google sign-in is not configured.")
    state = issue_oauth_state(session_secret.get_secret_value())
    return RedirectResponse(build_authorization_url(settings, state), status_code=302)


@router.get(
    "/google/callback",
    summary="Google sign-in callback",
    response_class=RedirectResponse,
)
def google_callback(
    settings: SettingsDep,
    session: DbSession,
    client: HttpClient,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Finish Google sign-in: verify the state, swap the code, sign the user
    in, and send the browser back to the frontend. The session token travels
    as an HttpOnly cookie on the redirect, never in the URL. Every failure
    (Google sent an `error`, a bad state, a failed token exchange or
    verification) redirects to the frontend sign-in page with an error flag
    instead of returning a JSON error to the browser."""
    if error is not None:
        logger.info("Google sign-in did not complete: %s", error)
        return _sign_in_failed(settings)
    session_secret = settings.session_secret
    if (
        not settings.google_configured
        or session_secret is None
        or code is None
        or state is None
        or not verify_oauth_state(state, session_secret.get_secret_value())
    ):
        logger.info("Google sign-in callback rejected: missing or invalid parameters")
        return _sign_in_failed(settings)
    try:
        id_token = exchange_code(client, settings, code)
        client_id = settings.google_client_id or ""
        profile = verify_id_token(client, id_token, client_id)
        user = upsert_google_user(session, profile)
        session.commit()
    except IntegrityError:
        session.rollback()
        logger.info("Google sign-in failed while storing the user")
        return _sign_in_failed(settings)
    except Exception:
        session.rollback()
        logger.exception("Google sign-in failed during the callback")
        return _sign_in_failed(settings)
    token = issue_session_token(
        session_secret.get_secret_value(),
        user_id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        demo=False,
    )
    response = RedirectResponse(f"{settings.frontend_url}/auth/callback", status_code=302)
    set_session_cookie(response, token, production=settings.is_production)
    return response


@router.post(
    "/demo-login",
    summary="Demo sign-in (no Google account)",
    responses=error_responses(404),
)
def demo_login(response: Response, settings: SettingsDep, session: DbSession) -> SessionResponse:
    """Sign in as the clearly-labelled local demo user. Only available while
    Google sign-in is unconfigured; disabled as soon as Google is set up.
    The session token travels as an HttpOnly cookie, never in the body."""
    session_secret = settings.session_secret
    if settings.google_configured or session_secret is None:
        raise NotFoundError("Demo sign-in is not available.")
    user = get_or_create_demo_user(session)
    session.commit()
    token = issue_session_token(
        session_secret.get_secret_value(),
        user_id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        demo=True,
    )
    set_session_cookie(response, token, production=settings.is_production)
    return SessionResponse(user=_user_response(user), demo=True)


@router.post("/logout", summary="Sign out")
def logout(response: Response, settings: SettingsDep) -> LogoutResponse:
    """Sign out: expire the session cookie. The token itself is stateless,
    so there is nothing else to clear server-side."""
    clear_session_cookie(response, production=settings.is_production)
    return LogoutResponse(signed_out=True)


@router.get("/me", summary="Current principal", responses=error_responses(401))
def me(principal: CurrentPrincipal) -> MeResponse:
    return MeResponse(
        subject=principal.subject,
        email=principal.email,
        name=principal.name,
        picture_url=principal.picture_url,
        demo=principal.demo,
    )
