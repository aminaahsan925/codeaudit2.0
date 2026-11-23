"""Domain verification: token file or home-page meta tag. The fixture
server is local, so verification needs settings that allow loopback.
"""

import pytest
from live_test_server import LiveTestServer, RouteResponse

from app.services.live.verify import VERIFICATION_PATH, verify_domain

TOKEN = "launchaudit-verify-7f3a9c2e"  # noqa: S105 - fake test value, not a secret


@pytest.fixture
def live_server():
    with LiveTestServer() as server:
        yield server


@pytest.fixture
def loopback_settings(settings_factory):
    return settings_factory(allow_loopback_live_checks=True)


def test_token_file_verifies(live_server, loopback_settings):
    live_server.routes[VERIFICATION_PATH] = RouteResponse(status=200, body=TOKEN)
    assert verify_domain(live_server.url, TOKEN, loopback_settings) is True


def test_token_file_with_surrounding_whitespace_verifies(live_server, loopback_settings):
    live_server.routes[VERIFICATION_PATH] = RouteResponse(status=200, body=f"\n  {TOKEN}\n")
    assert verify_domain(live_server.url, TOKEN, loopback_settings) is True


def test_wrong_token_in_file_does_not_verify(live_server, loopback_settings):
    live_server.routes[VERIFICATION_PATH] = RouteResponse(status=200, body="some-other-token")
    live_server.routes["/"] = RouteResponse(status=200, body="<html></html>")
    assert verify_domain(live_server.url, TOKEN, loopback_settings) is False


def test_meta_tag_verifies(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200,
        body=(
            f'<html><head><meta name="launchaudit-verification" content="{TOKEN}"></head></html>'
        ),
    )
    assert verify_domain(live_server.url, TOKEN, loopback_settings) is True


def test_meta_tag_with_reversed_attributes_verifies(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200,
        body=(
            f'<html><head><meta content="{TOKEN}" name="launchaudit-verification"></head></html>'
        ),
    )
    assert verify_domain(live_server.url, TOKEN, loopback_settings) is True


def test_meta_tag_with_wrong_token_does_not_verify(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200,
        body=(
            '<html><head><meta name="launchaudit-verification" content="wrong-token"></head></html>'
        ),
    )
    assert verify_domain(live_server.url, TOKEN, loopback_settings) is False


def test_nothing_served_does_not_verify(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(status=200, body="<html></html>")
    assert verify_domain(live_server.url, TOKEN, loopback_settings) is False


def test_unreachable_does_not_verify(loopback_settings):
    with LiveTestServer() as server:
        closed_url = server.url
    assert verify_domain(closed_url, TOKEN, loopback_settings) is False


def test_blocked_target_does_not_verify(live_server):
    # No settings passed: loopback stays blocked, so verification fails
    # instead of probing the local address.
    live_server.routes[VERIFICATION_PATH] = RouteResponse(status=200, body=TOKEN)
    assert verify_domain(live_server.url, TOKEN) is False


def test_empty_token_or_url_does_not_verify(live_server, loopback_settings):
    assert verify_domain(live_server.url, "", loopback_settings) is False
    assert verify_domain("", TOKEN, loopback_settings) is False
