"""Broken links and forms check, against local fixture servers.

No test here needs the network: the app under test is a LiveTestServer on
127.0.0.1, reachable because the test settings allow loopback live checks.
A second server stands in for another origin, so off-origin behaviour can
be proven by its (zero) hit count rather than by trusting the code.
"""

import pytest
from live_test_server import LiveTestServer, RouteResponse

from app.schemas.finding import FindingEngine, Severity
from app.services.live.crawl import MAX_PAGES
from app.services.live.runner import run_live_checks
from app.services.live.verify import DomainNotVerifiedError

ALL_SECURITY_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Content-Security-Policy", "default-src 'self'"),
    ("Strict-Transport-Security", "max-age=31536000"),
]


@pytest.fixture
def live_server():
    with LiveTestServer() as server:
        yield server


@pytest.fixture
def loopback_settings(settings_factory):
    return settings_factory(allow_loopback_live_checks=True)


def set_home(server, body):
    server.routes["/"] = RouteResponse(status=200, headers=list(ALL_SECURITY_HEADERS), body=body)


def findings_for(findings, rule_id):
    return [f for f in findings if f.rule_id == rule_id]


def counting_route(hits, body="", status=200):
    """A route that records every request path it serves."""

    def _route(handler):
        hits.append(handler.path)
        return RouteResponse(status=status, body=body)

    return _route


def test_broken_links_found_with_proof(live_server, loopback_settings):
    set_home(
        live_server,
        '<html><body><a href="/ok">ok</a><a href="/missing">gone</a>'
        '<a href="/error">bust</a></body></html>',
    )
    live_server.routes["/ok"] = RouteResponse(status=200, body="fine")
    live_server.routes["/missing"] = RouteResponse(status=404, body="not here")
    live_server.routes["/error"] = RouteResponse(status=500, body="boom")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)

    broken = findings_for(findings, "BROKEN_LINK")
    assert {f.evidence.http.url for f in broken if f.evidence.http} == {
        live_server.url + "/missing",
        live_server.url + "/error",
    }
    by_status = {f.evidence.http.status: f for f in broken if f.evidence.http}
    assert set(by_status) == {404, 500}
    for finding in broken:
        assert finding.severity == Severity.MEDIUM
        assert finding.engine == FindingEngine.LIVE
        assert finding.evidence.http is not None
        assert finding.evidence.http.url in (finding.evidence.notes or "")
        assert live_server.url + "/" in (finding.evidence.notes or "")
        assert "Why it matters" in (finding.fix_guidance or "")
        assert "How to fix" in (finding.fix_guidance or "")


def test_good_links_not_flagged(live_server, loopback_settings):
    set_home(
        live_server,
        '<html><body><a href="/ok">ok</a><a href="#section">anchor</a>'
        '<a href="mailto:hi@example.com">mail</a>'
        '<a href="javascript:void(0)">js</a></body></html>',
    )
    live_server.routes["/ok"] = RouteResponse(status=200, body="fine")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert findings_for(findings, "BROKEN_LINK") == []
    assert findings_for(findings, "BROKEN_FORM") == []


def test_off_origin_links_never_fetched(live_server, loopback_settings):
    hits: list[str] = []
    with LiveTestServer() as other_origin:
        other_origin.routes["/page"] = counting_route(hits, body="other site")
        set_home(
            live_server,
            f'<html><body><a href="{other_origin.url}/page">elsewhere</a>'
            '<a href="https://example.com/dead">far away</a></body></html>',
        )
        findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert hits == []
    assert findings_for(findings, "BROKEN_LINK") == []


def test_page_cap_respected(live_server, loopback_settings):
    hits: list[str] = []
    pages = 25
    set_home(live_server, '<html><body><a href="/p1">next</a></body></html>')
    for number in range(1, pages + 1):
        nxt = f'<a href="/p{number + 1}">next</a>' if number < pages else ""
        live_server.routes[f"/p{number}"] = counting_route(
            hits, body=f"<html><body>{nxt}</body></html>"
        )
    run_live_checks(live_server.url, loopback_settings, verified=True)

    fetched = {path for path in hits if path.startswith("/p")}
    # Home is page 1, so pages p1..p19 are crawled (parsed); p20 is only
    # status-checked as a link target, never parsed, so p21+ is never seen.
    assert fetched <= {f"/p{n}" for n in range(1, MAX_PAGES + 1)}
    assert "/p21" not in fetched
    assert "/p25" not in fetched


def test_no_crawl_when_unverified(live_server, loopback_settings):
    hits: list[str] = []
    live_server.routes["/"] = counting_route(
        hits,
        body='<html><body><a href="/missing">gone</a></body></html>',
    )
    with pytest.raises(DomainNotVerifiedError):
        run_live_checks(live_server.url, loopback_settings, verified=False)
    assert hits == []


def test_broken_link_deduped_across_pages(live_server, loopback_settings):
    link = '<a href="/missing">gone</a>'
    set_home(live_server, f'<html><body>{link}<a href="/a">a</a></body></html>')
    live_server.routes["/a"] = RouteResponse(
        status=200, body=f'<html><body>{link}<a href="/b">b</a></body></html>'
    )
    live_server.routes["/b"] = RouteResponse(status=200, body=f"<html><body>{link}</body></html>")
    live_server.routes["/missing"] = RouteResponse(status=404, body="not here")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)

    broken = findings_for(findings, "BROKEN_LINK")
    assert len(broken) == 1
    assert "3 pages" in (broken[0].evidence.notes or "")


def test_broken_link_findings_capped(live_server, loopback_settings):
    links = "".join(f'<a href="/bad{n}">bad</a>' for n in range(25))
    set_home(live_server, f"<html><body>{links}</body></html>")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    # Unmapped paths return 404, so all 25 links are broken; findings cap at 20.
    assert len(findings_for(findings, "BROKEN_LINK")) == 20


def test_broken_forms_found(live_server, loopback_settings):
    set_home(
        live_server,
        "<html><body>"
        "<form><input name='q'></form>"
        "<form method='delete' action='/ok'><input></form>"
        "<form method='post' action='/missing'><input></form>"
        "<form method='post' action='/ok'><input></form>"
        "<form action='/ok'><input></form>"
        "</body></html>",
    )
    live_server.routes["/ok"] = RouteResponse(status=200, body="fine")
    live_server.routes["/missing"] = RouteResponse(status=404, body="not here")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)

    broken = findings_for(findings, "BROKEN_FORM")
    assert len(broken) == 3
    reasons = " | ".join(f.evidence.notes or "" for f in broken)
    assert "form has no action" in reasons
    assert "invalid method 'delete'" in reasons
    assert "form action returns 404" in reasons
    for finding in broken:
        assert finding.severity == Severity.MEDIUM
        assert finding.engine == FindingEngine.LIVE
        assert live_server.url + "/" in (finding.evidence.notes or "")
    action_finding = next(f for f in broken if f.evidence.http is not None)
    assert action_finding.evidence.http.status == 404
    assert action_finding.evidence.http.url.endswith("/missing")


def test_form_with_empty_action_flagged(live_server, loopback_settings):
    set_home(
        live_server,
        "<html><body><form action=''><input></form></body></html>",
    )
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    broken = findings_for(findings, "BROKEN_FORM")
    assert len(broken) == 1
    assert "form has no action" in (broken[0].evidence.notes or "")


def test_post_only_form_action_not_flagged(live_server, loopback_settings):
    # A POST-only endpoint answers GET with 405; the form still works,
    # so the action is not broken. (The demo shop's /cart/add is exactly
    # this shape.)
    set_home(
        live_server,
        "<html><body><form method='post' action='/cart/add'><input></form></body></html>",
    )
    live_server.routes["/cart/add"] = RouteResponse(status=405, body="Method Not Allowed")
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert findings_for(findings, "BROKEN_FORM") == []


def test_off_origin_form_action_not_checked(live_server, loopback_settings):
    hits: list[str] = []
    with LiveTestServer() as other_origin:
        other_origin.routes["/submit"] = counting_route(hits, status=500, body="bust")
        set_home(
            live_server,
            f"<html><body><form method='post' action='{other_origin.url}/submit'>"
            "<input></form></body></html>",
        )
        findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert hits == []
    assert findings_for(findings, "BROKEN_FORM") == []
