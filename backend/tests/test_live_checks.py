"""Live checks against a local fixture server. No test here needs the
network: the app under test is a LiveTestServer on 127.0.0.1, reachable
because the test settings allow loopback live checks.
"""

import pytest
from live_test_server import LiveTestServer, RouteResponse

from app.schemas.finding import FindingEngine, Severity
from app.services.live.checks import missing_cookie_flags
from app.services.live.runner import run_live_checks, run_live_checks_detailed
from app.services.live.verify import DomainNotVerifiedError

ALL_SECURITY_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Content-Security-Policy", "default-src 'self'"),
    ("Strict-Transport-Security", "max-age=31536000"),
]

CLEAN_HOME = "<html><head></head><body>ok</body></html>"


@pytest.fixture
def live_server():
    with LiveTestServer() as server:
        yield server


@pytest.fixture
def loopback_settings(settings_factory):
    return settings_factory(allow_loopback_live_checks=True)


def set_clean_home(server):
    server.routes["/"] = RouteResponse(
        status=200, headers=list(ALL_SECURITY_HEADERS), body=CLEAN_HOME
    )


def rule_ids(findings):
    return sorted(f.rule_id for f in findings)


def finding_for(findings, rule_id):
    return next(f for f in findings if f.rule_id == rule_id)


def test_clean_app_has_no_findings(live_server, loopback_settings):
    set_clean_home(live_server)
    result = run_live_checks_detailed(live_server.url, loopback_settings, verified=True)
    assert result.status == "done"
    assert result.findings == []
    assert result.skipped_checks == []


def test_exposed_env_flagged(live_server, loopback_settings):
    set_clean_home(live_server)
    live_server.routes["/.env"] = RouteResponse(
        status=200, body="APP_NAME=demo-app\nDEBUG=False\nPORT=8000\n"
    )
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == ["EXPOSED_ENV"]
    finding = findings[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.engine == FindingEngine.LIVE
    assert finding.evidence.http is not None
    assert finding.evidence.http.status == 200
    assert finding.evidence.http.url.endswith("/.env")
    assert "Why it matters" in (finding.fix_guidance or "")
    assert "How to fix" in (finding.fix_guidance or "")


def test_env_without_env_content_not_flagged(live_server, loopback_settings):
    set_clean_home(live_server)
    live_server.routes["/.env"] = RouteResponse(status=200, body="nothing here\n")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == []


def test_exposed_git_flagged(live_server, loopback_settings):
    set_clean_home(live_server)
    live_server.routes["/.git/HEAD"] = RouteResponse(status=200, body="ref: refs/heads/main\n")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == ["EXPOSED_GIT"]
    assert findings[0].severity == Severity.HIGH


def test_js_bundle_secret_flagged_and_masked(live_server, loopback_settings):
    set_clean_home(live_server)
    live_server.routes["/"] = RouteResponse(
        status=200,
        headers=list(ALL_SECURITY_HEADERS),
        body='<html><head><script src="/static/app.js"></script></head></html>',
    )
    # Fake key-shaped value for the masking test only, never a real key.
    live_server.routes["/static/app.js"] = RouteResponse(
        status=200,
        body='const key = "sk_test_abcdefgh12345678";\n',  # gitleaks:allow
    )
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == ["SECRETS_IN_JS_BUNDLE"]
    finding = findings[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence.http is not None
    assert finding.evidence.http.body_excerpt is not None
    assert "abcdefgh12345678" not in finding.evidence.http.body_excerpt
    assert "abcdefgh12345678" not in (finding.snippet or "")
    assert "sk_t" in finding.evidence.http.body_excerpt


def test_js_bundle_without_secrets_not_flagged(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200,
        headers=list(ALL_SECURITY_HEADERS),
        body='<html><head><script src="/static/app.js"></script></head></html>',
    )
    live_server.routes["/static/app.js"] = RouteResponse(status=200, body="console.log('hello');\n")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == []


def test_cross_origin_bundle_not_fetched(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200,
        headers=list(ALL_SECURITY_HEADERS),
        body=('<html><head><script src="https://cdn.example.com/x.js"></script></head></html>'),
    )
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == []


def test_at_most_three_bundles_fetched(live_server, loopback_settings):
    requested: list[str] = []

    def bundle(handler):
        requested.append(handler.path)
        return RouteResponse(status=200, body="console.log('ok');\n")

    scripts = "".join(f'<script src="/static/b{i}.js"></script>' for i in range(5))
    live_server.routes["/"] = RouteResponse(
        status=200,
        headers=list(ALL_SECURITY_HEADERS),
        body=f"<html><head>{scripts}</head></html>",
    )
    for i in range(5):
        live_server.routes[f"/static/b{i}.js"] = bundle
    run_live_checks(live_server.url, loopback_settings, verified=True)
    assert len(requested) == 3


@pytest.mark.parametrize("missing_count", [2, 3, 5])
def test_missing_security_headers_flagged(live_server, loopback_settings, missing_count):
    kept = ALL_SECURITY_HEADERS[: 5 - missing_count]
    live_server.routes["/"] = RouteResponse(status=200, headers=list(kept), body=CLEAN_HOME)
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == ["MISSING_SECURITY_HEADERS"]
    assert findings[0].severity == Severity.MEDIUM


def test_one_missing_header_not_flagged(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200, headers=list(ALL_SECURITY_HEADERS[:4]), body=CLEAN_HOME
    )
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == []


@pytest.mark.parametrize("allow_origin", ["*", "https://evil.example"])
def test_cors_open_flagged(live_server, loopback_settings, allow_origin):
    def home(handler):
        headers = list(ALL_SECURITY_HEADERS)
        if handler.headers.get("Origin") == "https://evil.example":
            headers.append(("Access-Control-Allow-Origin", allow_origin))
        return RouteResponse(status=200, headers=headers, body=CLEAN_HOME)

    live_server.routes["/"] = home
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == ["CORS_OPEN"]
    assert findings[0].severity == Severity.MEDIUM


def test_cors_closed_not_flagged(live_server, loopback_settings):
    def home(handler):
        headers = list(ALL_SECURITY_HEADERS)
        headers.append(("Access-Control-Allow-Origin", "https://shop.example"))
        return RouteResponse(status=200, headers=headers, body=CLEAN_HOME)

    live_server.routes["/"] = home
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == []


def test_insecure_cookie_flagged(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200,
        headers=[*ALL_SECURITY_HEADERS, ("Set-Cookie", "session=abc123; Path=/")],
        body=CLEAN_HOME,
    )
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == ["INSECURE_COOKIE"]
    finding = findings[0]
    assert finding.severity == Severity.MEDIUM
    assert finding.evidence.http is not None
    # The cookie value itself must not leak into the evidence headers.
    assert "abc123" not in str(finding.evidence.http.response_headers)


def test_secure_cookie_not_flagged(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200,
        headers=[
            *ALL_SECURITY_HEADERS,
            ("Set-Cookie", "session=abc123; Path=/; HttpOnly; SameSite=Lax"),
        ],
        body=CLEAN_HOME,
    )
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == []


def test_insecure_login_cookie_flagged(live_server, loopback_settings):
    set_clean_home(live_server)
    live_server.routes["/login"] = RouteResponse(
        status=200,
        headers=[("Set-Cookie", "auth=xyz; Path=/")],
        body="logged in",
    )
    findings = run_live_checks(
        live_server.url,
        loopback_settings,
        verified=True,
        email="tester@launchaudit.local",
        password="TestPass123",  # noqa: S106 - fake test account, fixture only
    )
    assert rule_ids(findings) == ["INSECURE_COOKIE"]
    assert findings[0].evidence.notes == "Path: /login"


@pytest.mark.parametrize(
    ("secure", "httponly", "samesite", "is_https", "expected"),
    [
        (False, False, False, False, ["HttpOnly", "SameSite"]),
        (False, True, True, False, []),
        (True, True, True, True, []),
        (False, True, True, True, ["Secure"]),
        (False, True, False, True, ["SameSite", "Secure"]),
    ],
)
def test_missing_cookie_flags(secure, httponly, samesite, is_https, expected):
    assert (
        missing_cookie_flags(secure=secure, httponly=httponly, samesite=samesite, is_https=is_https)
        == expected
    )


def test_open_admin_routes_flagged(live_server, loopback_settings):
    set_clean_home(live_server)
    live_server.routes["/admin"] = RouteResponse(status=200, body="admin panel")
    live_server.routes["/debug"] = RouteResponse(
        status=302, headers=[("Location", "/login")], body=""
    )
    live_server.routes["/debug/pprof"] = RouteResponse(status=200, body="profiles")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    admin = [f for f in findings if f.rule_id == "OPEN_ADMIN_ROUTE"]
    assert len(admin) == 2
    assert {f.evidence.notes for f in admin} == {
        "Path: /admin",
        "Path: /debug/pprof",
    }
    assert all(f.severity == Severity.MEDIUM for f in admin)


def test_broken_app_flags_everything(live_server, loopback_settings):
    live_server.routes["/"] = RouteResponse(
        status=200,
        headers=[("Set-Cookie", "session=abc123; Path=/")],
        body='<html><head><script src="/static/app.js"></script></head></html>',
    )
    live_server.routes["/.env"] = RouteResponse(status=200, body="APP_NAME=demo-app\nDEBUG=False\n")
    live_server.routes["/.git/HEAD"] = RouteResponse(status=200, body="ref: refs/heads/main\n")
    # Fake key-shaped value for the masking test only, never a real key.
    live_server.routes["/static/app.js"] = RouteResponse(
        status=200,
        body='const key = "sk_test_abcdefgh12345678";\n',  # gitleaks:allow
    )
    live_server.routes["/admin"] = RouteResponse(status=200, body="admin panel")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == [
        "EXPOSED_ENV",
        "EXPOSED_GIT",
        "INSECURE_COOKIE",
        "MISSING_SECURITY_HEADERS",
        "OPEN_ADMIN_ROUTE",
        "SECRETS_IN_JS_BUNDLE",
    ]
    for finding in findings:
        assert finding.engine == FindingEngine.LIVE
        assert finding.fix_guidance is not None
        assert "## Why it matters" in finding.fix_guidance
        assert "## How to fix" in finding.fix_guidance
        assert finding.evidence.http is not None
        assert finding.evidence.http.method in ("GET", "POST")
        assert finding.evidence.http.status >= 100
        excerpt = finding.evidence.http.body_excerpt
        assert excerpt is None or len(excerpt) <= 500


def test_unreachable_app_is_skipped_not_a_finding(loopback_settings):
    with LiveTestServer() as server:
        closed_url = server.url
    # The server is shut down now, so the port refuses connections.
    result = run_live_checks_detailed(closed_url, loopback_settings, verified=True)
    assert result.status == "skipped"
    assert result.findings == []
    assert "could not reach" in (result.skipped_reason or "")


def test_unverified_domain_refused(live_server, loopback_settings):
    set_clean_home(live_server)
    with pytest.raises(DomainNotVerifiedError):
        run_live_checks(live_server.url, loopback_settings, verified=False)


def test_blocked_target_is_skipped(live_server, settings_factory):
    set_clean_home(live_server)
    settings = settings_factory(allow_loopback_live_checks=False)
    result = run_live_checks_detailed(live_server.url, settings, verified=True)
    assert result.status == "skipped"
    assert result.findings == []
    assert "blocked" in (result.skipped_reason or "")


def test_missing_url_is_skipped(loopback_settings):
    result = run_live_checks_detailed("", loopback_settings, verified=True)
    assert result.status == "skipped"
    assert result.findings == []
