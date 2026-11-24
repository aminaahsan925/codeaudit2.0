"""Speed and accessibility quick checks, against a local fixture server.

No test here needs the network: the app under test is a LiveTestServer on
127.0.0.1, reachable because the test settings allow loopback live checks.
Slow pages are simulated by sleeping before the server answers, which
delays the headers (TTFB) and therefore the full load by the same amount.
"""

import re
import time

import httpx
import pytest
from live_test_server import LiveTestServer, RouteResponse

from app.schemas.finding import FindingEngine, Severity
from app.services.live.perf_a11y import (
    check_accessibility,
    check_speed,
    check_speed_a11y,
)
from app.services.live.runner import run_live_checks
from app.services.live.ssrf_client import SsrfSafeClient
from app.services.live.verify import DomainNotVerifiedError

ALL_SECURITY_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Content-Security-Policy", "default-src 'self'"),
    ("Strict-Transport-Security", "max-age=31536000"),
]

# Clean for every a11y rule: lang, title, alt text (including a decorative
# empty alt), and one input labelled each way (label[for], wrapping label,
# aria-label, aria-labelledby), plus a label that comes AFTER its input,
# a hidden input, and a submit button, none of which need a label.
CLEAN_HOME = """<html lang="en"><head><title>Demo Shop</title></head><body>
<img src="/img/logo.png" alt="Demo Shop logo">
<img src="/img/spacer.png" alt="">
<form>
<label for="email">Email</label>
<input id="email" name="email" type="email">
<label>Name <input name="name" type="text"></label>
<input name="search" type="search" aria-label="Search products">
<input id="city" name="city" type="text" aria-labelledby="city-label">
<span id="city-label">City</span>
<input id="later" name="later" type="text">
<label for="later">Later label</label>
<input type="hidden" name="product_id" value="42">
<input type="submit" value="Send">
</form>
</body></html>"""

# Dirty for every a11y rule: no lang, no title, two images without alt,
# two inputs without any label.
DIRTY_HOME = """<html><head></head><body>
<img src="/img/logo.png" alt="Demo Shop logo">
<img src="/img/hero.jpg">
<img src="/img/badge.png">
<form>
<label for="email">Email</label>
<input id="email" name="email" type="email">
<input name="phone" type="tel">
<input name="notes" type="text">
</form>
</body></html>"""


@pytest.fixture
def live_server():
    with LiveTestServer() as server:
        yield server


@pytest.fixture
def loopback_settings(settings_factory):
    return settings_factory(allow_loopback_live_checks=True)


def _home_response(html: str) -> httpx.Response:
    return httpx.Response(200, text=html, request=httpx.Request("GET", "http://example.com/"))


def _set_home(server, body=CLEAN_HOME):
    server.routes["/"] = RouteResponse(status=200, headers=list(ALL_SECURITY_HEADERS), body=body)


def _set_slow_home(server, delay_seconds, body=CLEAN_HOME):
    def home(handler):
        time.sleep(delay_seconds)
        return RouteResponse(status=200, headers=list(ALL_SECURITY_HEADERS), body=body)

    server.routes["/"] = home


def rule_ids(findings):
    return sorted(f.rule_id for f in findings)


def finding_for(findings, rule_id):
    return next(f for f in findings if f.rule_id == rule_id)


def _ms_in_snippet(finding):
    match = re.search(r"(\d+) ms", finding.snippet or "")
    assert match is not None, f"no measured ms in snippet: {finding.snippet!r}"
    return int(match.group(1))


# ------------------------------------------------------------------- speed


def test_fast_page_has_no_speed_findings(live_server):
    _set_home(live_server)
    with SsrfSafeClient(allow_loopback=True) as client:
        assert check_speed(client, live_server.url) == []


def test_slow_ttfb_is_medium(live_server):
    _set_slow_home(live_server, 1.0)
    with SsrfSafeClient(allow_loopback=True) as client:
        findings = check_speed(client, live_server.url)
    assert rule_ids(findings) == ["SLOW_TTFB"]
    finding = findings[0]
    assert finding.severity == Severity.MEDIUM
    assert finding.engine == FindingEngine.LIVE
    assert _ms_in_snippet(finding) >= 800
    assert "Path: /" in (finding.evidence.notes or "")
    assert finding.evidence.http is not None
    assert finding.evidence.http.status == 200


def test_slow_load_is_medium(live_server):
    # A 3.2 s delay pushes the full load over 3000 ms (Medium) and the
    # TTFB over 2000 ms (High) at the same time.
    _set_slow_home(live_server, 3.2)
    with SsrfSafeClient(allow_loopback=True) as client:
        findings = check_speed(client, live_server.url)
    assert rule_ids(findings) == ["SLOW_LOAD", "SLOW_TTFB"]
    assert finding_for(findings, "SLOW_LOAD").severity == Severity.MEDIUM
    assert finding_for(findings, "SLOW_TTFB").severity == Severity.HIGH
    assert _ms_in_snippet(finding_for(findings, "SLOW_LOAD")) >= 3000
    assert _ms_in_snippet(finding_for(findings, "SLOW_TTFB")) >= 2000


def test_very_slow_page_is_high(live_server):
    _set_slow_home(live_server, 8.3)
    with SsrfSafeClient(allow_loopback=True) as client:
        findings = check_speed(client, live_server.url)
    assert rule_ids(findings) == ["SLOW_LOAD", "SLOW_TTFB"]
    assert finding_for(findings, "SLOW_LOAD").severity == Severity.HIGH
    assert finding_for(findings, "SLOW_TTFB").severity == Severity.HIGH
    assert _ms_in_snippet(finding_for(findings, "SLOW_LOAD")) >= 8000
    assert _ms_in_snippet(finding_for(findings, "SLOW_TTFB")) >= 8000


def test_get_timed_returns_sane_timings(live_server):
    _set_home(live_server)
    with SsrfSafeClient(allow_loopback=True) as client:
        timed = client.get_timed(live_server.url + "/")
    assert timed.response.status_code == 200
    assert 0 <= timed.ttfb_ms <= timed.load_ms


def test_get_timed_follows_redirect(live_server):
    live_server.routes["/"] = RouteResponse(status=302, headers=[("Location", "/final")], body="")
    live_server.routes["/final"] = RouteResponse(status=200, body="final page")
    with SsrfSafeClient(allow_loopback=True) as client:
        timed = client.get_timed(live_server.url + "/")
    assert timed.response.status_code == 200
    assert str(timed.response.url).endswith("/final")
    assert timed.response.text == "final page"


# ------------------------------------------------------------ accessibility


def test_dirty_page_flags_all_four_a11y_rules():
    findings = check_accessibility(_home_response(DIRTY_HOME))
    assert rule_ids(findings) == [
        "IMG_MISSING_ALT",
        "INPUT_MISSING_LABEL",
        "MISSING_LANG",
        "MISSING_TITLE",
    ]
    assert all(f.severity == Severity.LOW for f in findings)
    assert all(f.engine == FindingEngine.LIVE for f in findings)

    alt = finding_for(findings, "IMG_MISSING_ALT")
    assert "2 images" in (alt.snippet or "")
    assert "/img/hero.jpg" in (alt.snippet or "")
    assert "/img/badge.png" in (alt.snippet or "")
    assert "/img/logo.png" not in (alt.snippet or "")

    inputs = finding_for(findings, "INPUT_MISSING_LABEL")
    assert "2 inputs" in (inputs.snippet or "")
    assert "phone (tel)" in (inputs.snippet or "")
    assert "notes (text)" in (inputs.snippet or "")
    assert "email" not in (inputs.snippet or "")

    for finding in findings:
        assert "Path: /" in (finding.evidence.notes or "")
        assert finding.evidence.http is not None
        assert finding.evidence.http.status == 200
        assert "## Why it matters" in (finding.fix_guidance or "")
        assert "## How to fix" in (finding.fix_guidance or "")


def test_clean_page_has_no_a11y_findings():
    assert check_accessibility(_home_response(CLEAN_HOME)) == []


def test_empty_title_flagged():
    html = '<html lang="en"><head><title>   </title></head><body>ok</body></html>'
    findings = check_accessibility(_home_response(html))
    assert rule_ids(findings) == ["MISSING_TITLE"]
    assert "empty" in (findings[0].snippet or "")


def test_missing_title_snippet_names_the_missing_element():
    html = '<html lang="en"><head></head><body>ok</body></html>'
    findings = check_accessibility(_home_response(html))
    assert rule_ids(findings) == ["MISSING_TITLE"]
    assert "no <title>" in (findings[0].snippet or "")


# ------------------------------------------------------- runner integration


def test_dirty_page_flags_a11y_through_runner(live_server, loopback_settings):
    _set_home(live_server, body=DIRTY_HOME)
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == [
        "IMG_MISSING_ALT",
        "INPUT_MISSING_LABEL",
        "MISSING_LANG",
        "MISSING_TITLE",
    ]


def test_clean_fast_page_has_no_speed_a11y_findings(live_server, loopback_settings):
    _set_home(live_server)
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert findings == []


def test_slow_page_flags_speed_through_runner(live_server, loopback_settings):
    _set_slow_home(live_server, 1.0)
    findings = run_live_checks(live_server.url, loopback_settings, verified=True)
    assert rule_ids(findings) == ["SLOW_TTFB"]
    assert finding_for(findings, "SLOW_TTFB").severity == Severity.MEDIUM


def test_unverified_domain_runs_no_checks(live_server, loopback_settings):
    hits: list[str] = []

    def home(handler):
        hits.append(handler.path)
        return RouteResponse(status=200, headers=list(ALL_SECURITY_HEADERS), body=CLEAN_HOME)

    live_server.routes["/"] = home
    with pytest.raises(DomainNotVerifiedError):
        run_live_checks(live_server.url, loopback_settings, verified=False)
    assert hits == []


def test_speed_failure_keeps_a11y_findings():
    """A timed fetch that fails drops the speed findings only."""

    class _FailingClient:
        def get_timed(self, url):
            raise httpx.ConnectError("refused", request=httpx.Request("GET", url))

    findings = check_speed_a11y(_FailingClient(), "http://example.com", _home_response(DIRTY_HOME))
    assert rule_ids(findings) == [
        "IMG_MISSING_ALT",
        "INPUT_MISSING_LABEL",
        "MISSING_LANG",
        "MISSING_TITLE",
    ]
