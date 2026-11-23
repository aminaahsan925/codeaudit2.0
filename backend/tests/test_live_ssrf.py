"""SSRF protection for the live-check client. No test here needs the network:
blocked targets are IP literals or a stubbed resolver, and redirect tests
use httpx.MockTransport.
"""

import socket

import httpx
import pytest

from app.services.live import ssrf_client
from app.services.live.ssrf_client import (
    SsrfBlockedError,
    SsrfSafeClient,
    TooManyRedirectsError,
    assert_url_allowed,
    loopback_allowed,
)

BLOCKED_TARGETS = [
    "http://127.0.0.1/",
    "http://127.0.0.2:8080/admin",
    "http://10.0.0.5/",
    "http://172.16.0.1/",
    "http://172.31.255.255/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://169.254.1.1/",
    "http://0.0.0.0/",
    "http://[::1]/",
    "http://[fe80::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://100.100.100.100/",
    "http://localhost:8000/",
    "ftp://example.com/file",
    "file:///etc/passwd",
    "http:///no-host",
    "http://example.com:99999/",
]


@pytest.mark.parametrize("url", BLOCKED_TARGETS)
def test_blocked_targets_rejected(url):
    with pytest.raises(SsrfBlockedError):
        assert_url_allowed(url, allow_loopback=False)


def test_public_ip_allowed():
    assert_url_allowed("http://93.184.216.34/", allow_loopback=False)


def test_hostname_resolving_to_private_is_blocked(monkeypatch):
    monkeypatch.setattr(ssrf_client, "resolve_host", lambda host, port: ["10.1.2.3"])
    with pytest.raises(SsrfBlockedError):
        assert_url_allowed("http://evil.example/", allow_loopback=False)


def test_hostname_with_one_private_answer_is_blocked(monkeypatch):
    monkeypatch.setattr(
        ssrf_client, "resolve_host", lambda host, port: ["93.184.216.34", "192.168.0.9"]
    )
    with pytest.raises(SsrfBlockedError):
        assert_url_allowed("http://mixed.example/", allow_loopback=False)


def test_hostname_resolving_to_public_is_allowed(monkeypatch):
    monkeypatch.setattr(ssrf_client, "resolve_host", lambda host, port: ["93.184.216.34"])
    assert_url_allowed("http://example.com/", allow_loopback=False)


def test_unresolvable_hostname_is_blocked(monkeypatch):
    def _fail(host, port):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(ssrf_client, "resolve_host", _fail)
    with pytest.raises(SsrfBlockedError):
        assert_url_allowed("http://does-not-resolve.example/", allow_loopback=False)


@pytest.mark.parametrize(
    ("allow_setting", "environment", "expected"),
    [
        (True, "test", True),
        (True, "development", True),
        (True, "production", False),
        (False, "test", False),
        (False, "development", False),
    ],
)
def test_loopback_allowed_needs_setting_and_non_production(
    settings_factory, allow_setting, environment, expected
):
    settings = settings_factory(allow_loopback_live_checks=allow_setting, environment=environment)
    assert loopback_allowed(settings) is expected


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:8000/", "http://10.0.0.5/", "http://192.168.1.1/"]
)
def test_loopback_and_private_allowed_with_setting(url):
    assert_url_allowed(url, allow_loopback=True)


@pytest.mark.parametrize(
    "url", ["http://169.254.169.254/", "http://169.254.1.1/", "http://100.100.100.100/"]
)
def test_metadata_and_link_local_still_blocked_with_setting(url):
    with pytest.raises(SsrfBlockedError):
        assert_url_allowed(url, allow_loopback=True)


def test_client_blocks_before_connecting():
    # Port 9 is closed: a ConnectError here would prove validation never ran.
    with SsrfSafeClient(allow_loopback=False) as client, pytest.raises(SsrfBlockedError):
        client.get("http://127.0.0.1:9/")


def test_client_uses_ten_second_timeout():
    assert ssrf_client.TIMEOUT_SECONDS == 10.0
    with SsrfSafeClient() as client:
        assert client._client.timeout.read == 10.0


def _public_resolver(monkeypatch):
    monkeypatch.setattr(ssrf_client, "resolve_host", lambda host, port: ["93.184.216.34"])


def test_redirect_to_private_is_blocked(monkeypatch):
    _public_resolver(monkeypatch)

    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "http://127.0.0.1:9/private"})
        return httpx.Response(200, text="ok")

    with (
        SsrfSafeClient(allow_loopback=False, transport=httpx.MockTransport(handler)) as client,
        pytest.raises(SsrfBlockedError),
    ):
        client.get("http://example.com/start")


def test_redirect_to_private_allowed_with_setting(monkeypatch):
    _public_resolver(monkeypatch)

    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "http://127.0.0.1:9/landed"})
        return httpx.Response(200, text="landed")

    with SsrfSafeClient(allow_loopback=True, transport=httpx.MockTransport(handler)) as client:
        response = client.get("http://example.com/start")
    assert response.status_code == 200
    assert response.text == "landed"


def test_redirect_to_public_is_followed(monkeypatch):
    _public_resolver(monkeypatch)

    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/landed"})
        return httpx.Response(200, text="landed")

    with SsrfSafeClient(allow_loopback=False, transport=httpx.MockTransport(handler)) as client:
        response = client.get("http://example.com/start")
    assert response.status_code == 200
    assert response.text == "landed"


def test_redirect_not_followed_when_disabled(monkeypatch):
    _public_resolver(monkeypatch)

    def handler(request):
        return httpx.Response(302, headers={"Location": "/landed"})

    with SsrfSafeClient(allow_loopback=False, transport=httpx.MockTransport(handler)) as client:
        response = client.get("http://example.com/start", follow_redirects=False)
    assert response.status_code == 302


def test_redirect_without_location_is_returned(monkeypatch):
    _public_resolver(monkeypatch)

    def handler(request):
        return httpx.Response(302)

    with SsrfSafeClient(allow_loopback=False, transport=httpx.MockTransport(handler)) as client:
        response = client.get("http://example.com/start")
    assert response.status_code == 302


def test_too_many_redirects(monkeypatch):
    _public_resolver(monkeypatch)

    def handler(request):
        return httpx.Response(302, headers={"Location": "/loop"})

    with (
        SsrfSafeClient(allow_loopback=False, transport=httpx.MockTransport(handler)) as client,
        pytest.raises(TooManyRedirectsError),
    ):
        client.get("http://example.com/loop")


def test_client_from_settings(settings_factory):
    settings = settings_factory(allow_loopback_live_checks=True)
    client = SsrfSafeClient.from_settings(settings)
    assert client._allow_loopback is True
    client.close()

    prod = settings_factory(allow_loopback_live_checks=True, environment="production")
    prod_client = SsrfSafeClient.from_settings(prod)
    assert prod_client._allow_loopback is False
    prod_client.close()
