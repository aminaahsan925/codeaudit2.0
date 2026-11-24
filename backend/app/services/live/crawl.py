"""Broken links and forms check: a bounded crawl of the verified live app.

Breadth-first from the home page, same origin only, at most MAX_PAGES
pages fetched. Every request goes through the SSRF-safe client, and the
check runs only inside run_all_checks, which the runner calls only after
domain verification, so an unverified domain is never crawled.

Findings:
- BROKEN_LINK [Medium]: a crawled link returns 4xx/5xx. Deduped by
  target URL; the proof notes every page that links to it.
- BROKEN_FORM [Medium]: a form with a missing or empty action, an
  invalid method, or a same-origin action URL that returns 404, 410, or
  5xx. The action is probed with GET, which can only prove the endpoint
  is missing or failing: a 405 means the endpoint exists but is
  POST-only (normal for a form), and other 4xx answers (400, 401, 403)
  likewise prove the path exists, so they are not findings. Deduped by
  (reason, action, method); off-origin actions are not checked, they
  belong to another site.

A link that cannot be fetched at all (timeout, DNS failure, blocked
target) is not a finding: only a real 4xx/5xx response proves a link is
broken. Response bodies are never stored in full; evidence keeps the
redacted excerpt the other live checks use.
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.schemas.finding import (
    Confidence,
    Evidence,
    Finding,
    FindingCategory,
    FindingEngine,
    HttpEvidence,
    Severity,
)
from app.services.scan.masking import mask_text

from .ssrf_client import SsrfBlockedError, SsrfSafeClient

MAX_PAGES = 20
MAX_PROOF = 500
MAX_LINK_FINDINGS = 20
MAX_FORM_FINDINGS = 20
# Status checks for link targets the crawl never fetched as a page
# (the page cap was hit first). Keeps one bad page from costing
# hundreds of requests.
MAX_LINK_CHECKS = 60

VALID_FORM_METHODS = {"get", "post"}
# A GET probe of a form action can only prove the endpoint is missing
# (404/410) or failing (5xx). 405 is the normal answer of a POST-only
# endpoint, and other 4xx answers prove the path exists.
BROKEN_FORM_ACTION_STATUSES = frozenset({404, 410})
# Schemes a link can carry that are not fetchable pages.
_NON_PAGE_SCHEMES = ("javascript:", "mailto:", "tel:", "data:")


@dataclass
class _FormGroup:
    """One broken form shape, with how many pages carry it."""

    reason: str
    page_url: str
    count: int
    action: str | None
    method: str | None
    response: httpx.Response | None
    tag: str | None


class _PageParser(HTMLParser):
    """Collect link targets and form tags from one HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.forms: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            href = attributes.get("href")
            if href:
                self.links.append(href)
        elif tag == "form":
            self.forms.append(
                {
                    "action": attributes.get("action"),
                    "method": attributes.get("method"),
                    "tag": self.get_starttag_text(),
                }
            )


def _same_origin(url: str, origin: str) -> bool:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}" == origin


def _is_html(response: httpx.Response) -> bool:
    """True when the page looks like HTML.

    A missing Content-Type counts as HTML: real servers send text/html,
    and a page with no header is still worth parsing. Only an explicit
    non-HTML type (image, PDF, JSON) skips parsing.
    """
    content_type = response.headers.get("content-type", "")
    return not content_type or content_type.split(";")[0].strip().lower() == "text/html"


def _is_broken_form_action(status: int) -> bool:
    """True when a GET probe proves a form action endpoint is unusable."""
    return status in BROKEN_FORM_ACTION_STATUSES or status >= 500


def _normalize_link(page_url: str, raw: str) -> str | None:
    """Resolve a raw href against its page, or None when not followable."""
    href = raw.strip()
    if not href or href.startswith("#"):
        return None
    if href.lower().startswith(_NON_PAGE_SCHEMES):
        return None
    absolute = urljoin(page_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    # Drop the fragment: #section links to the same page, not a new one.
    return parsed._replace(fragment="").geturl()


def redact_body(text: str | None) -> str | None:
    """Redact a response body for evidence: secrets masked, max 500 chars.

    Same redaction the other live checks apply (see checks.redact_body);
    defined here so this module does not import checks, which imports it.
    """
    if text is None:
        return None
    return mask_text(text)[:MAX_PROOF]


def _http_evidence(response: httpx.Response) -> HttpEvidence:
    headers = {
        name: mask_text(value)
        for name, value in response.headers.items()
        if name.lower() != "set-cookie"
    }
    return HttpEvidence(
        method=response.request.method,
        url=str(response.request.url),
        status=response.status_code,
        request_headers=dict(response.request.headers),
        response_headers=headers,
        body_excerpt=redact_body(response.text),
    )


def _fix_guidance(why_it_matters: str, how_to_fix: str) -> str:
    return f"## Why it matters\n\n{why_it_matters}\n\n## How to fix\n\n{how_to_fix}"


def _finding(
    *,
    rule_id: str,
    title: str,
    why_it_matters: str,
    how_to_fix: str,
    response: httpx.Response | None,
    notes: str,
    snippet: str | None = None,
) -> Finding:
    return Finding(
        id=uuid.uuid4(),
        rule_id=rule_id,
        engine=FindingEngine.LIVE,
        category=FindingCategory.OTHER,
        severity=Severity.MEDIUM,
        confidence=Confidence.HIGH,
        title=title,
        snippet=snippet,
        evidence=Evidence(
            http=_http_evidence(response) if response is not None else None,
            notes=notes,
        ),
        fix_guidance=_fix_guidance(why_it_matters, how_to_fix),
    )


def _broken_link_finding(
    target: str,
    response: httpx.Response,
    linking_pages: list[str],
) -> Finding:
    path = urlparse(target).path or target
    if len(linking_pages) == 1:
        linked_from = f"Linked from: {linking_pages[0]}"
    else:
        linked_from = f"Linked from {len(linking_pages)} pages, including: {linking_pages[0]}"
    return _finding(
        rule_id="BROKEN_LINK",
        title=f"Broken link: {path}",
        why_it_matters=(
            "Visitors who click this link hit an error page instead of the "
            "content they wanted, and search engines treat broken links as "
            "a sign the site is not maintained."
        ),
        how_to_fix=(
            "Fix the link target or remove the link. If the page moved, "
            "point the link at its new address (or add a redirect from the "
            "old one)."
        ),
        response=response,
        notes=f"Target: {target}\nStatus: {response.status_code}\n{linked_from}",
    )


def _broken_form_finding(
    *,
    reason: str,
    page_url: str,
    page_count: int,
    action: str | None,
    method: str | None,
    response: httpx.Response | None,
    tag: str | None,
) -> Finding:
    if page_count == 1:
        found_on = f"Found on: {page_url}"
    else:
        found_on = f"Found on {page_count} pages, including: {page_url}"
    details = [f"Reason: {reason}", f"Action: {action or '(missing)'}"]
    if method is not None:
        details.append(f"Method: {method}")
    if response is not None:
        details.append(f"Action status: {response.status_code}")
    return _finding(
        rule_id="BROKEN_FORM",
        title=f"Form cannot be submitted: {reason}",
        why_it_matters=(
            "A form that cannot be submitted silently drops whatever the "
            "visitor typed: signups, orders, and contact messages never "
            "arrive, and the visitor usually blames your site and leaves."
        ),
        how_to_fix=(
            "Give the form a working action URL that accepts its method, "
            "then submit it once yourself to confirm the data arrives."
        ),
        response=response,
        notes="\n".join([*details, found_on]),
        snippet=redact_body(tag) if tag else None,
    )


def check_broken_links_and_forms(
    client: SsrfSafeClient,
    base_url: str,
    home: httpx.Response,
) -> list[Finding]:
    """Crawl the live app from its home page and report broken links/forms.

    `home` is the home-page response run_all_checks already fetched, so
    the crawl does not fetch it twice. Returns at most MAX_LINK_FINDINGS
    BROKEN_LINK findings and MAX_FORM_FINDINGS BROKEN_FORM findings.
    """
    base_url = base_url.rstrip("/")
    origin = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
    home_url = base_url + "/"

    statuses: dict[str, httpx.Response | None] = {}
    link_sources: dict[str, list[str]] = {}
    forms: list[tuple[str, dict[str, str | None]]] = []

    def _parse_page(page_url: str, response: httpx.Response) -> list[str]:
        """Parse one fetched page; return its same-origin link targets."""
        if response.status_code != 200 or not _is_html(response):
            return []
        parser = _PageParser()
        parser.feed(response.text or "")
        for form in parser.forms:
            forms.append((page_url, form))
        targets: list[str] = []
        for raw in parser.links:
            target = _normalize_link(page_url, raw)
            if target is None or not _same_origin(target, origin):
                continue
            sources = link_sources.setdefault(target, [])
            if page_url not in sources:
                sources.append(page_url)
            targets.append(target)
        return targets

    # The home page is page 1 of the crawl, already fetched.
    statuses[home_url] = home
    visited = {home_url}
    queue: deque[str] = deque(_parse_page(home_url, home))

    # Breadth-first crawl, bounded to MAX_PAGES fetched pages.
    while queue and len(visited) < MAX_PAGES:
        page_url = queue.popleft()
        if page_url in visited:
            continue
        visited.add(page_url)
        try:
            response = client.get(page_url)
        except (httpx.HTTPError, SsrfBlockedError):
            statuses[page_url] = None
            continue
        statuses[page_url] = response
        for target in _parse_page(page_url, response):
            if target not in visited and target not in queue:
                queue.append(target)

    # Link targets the crawl never fetched (page cap hit first) still get
    # one status check each, within the check budget.
    checks_left = MAX_LINK_CHECKS
    for target in link_sources:
        if target in statuses or checks_left <= 0:
            continue
        checks_left -= 1
        try:
            statuses[target] = client.get(target)
        except (httpx.HTTPError, SsrfBlockedError):
            statuses[target] = None

    findings: list[Finding] = []

    broken_targets = sorted(
        target
        for target, response in statuses.items()
        if target in link_sources and response is not None and response.status_code >= 400
    )
    for target in broken_targets[:MAX_LINK_FINDINGS]:
        response = statuses[target]
        if response is None:  # filtered above; kept for the type checker
            continue
        findings.append(_broken_link_finding(target, response, link_sources[target]))

    # Forms: missing/empty action, invalid method, or a same-origin
    # action URL that answers 404, 410, or 5xx. Deduped by (reason, action,
    # method); off-origin actions are another site's problem.
    form_groups: dict[tuple[str, str | None, str | None], _FormGroup] = {}
    for page_url, form in forms:
        action = form.get("action")
        method = form.get("method")
        action_url: str | None = None
        response: httpx.Response | None = None
        if action is None or not action.strip():
            reason = "form has no action"
        elif (
            method is not None
            and method.strip()
            and method.strip().lower() not in VALID_FORM_METHODS
        ):
            reason = f"form uses invalid method {method.strip()!r}"
        else:
            action_url = _normalize_link(page_url, action)
            if action_url is None or not _same_origin(action_url, origin):
                continue
            response = statuses.get(action_url)
            if response is None and action_url not in statuses and checks_left > 0:
                checks_left -= 1
                try:
                    response = client.get(action_url)
                except (httpx.HTTPError, SsrfBlockedError):
                    response = None
                statuses[action_url] = response
            if response is None or not _is_broken_form_action(response.status_code):
                continue
            reason = f"form action returns {response.status_code}"
        key = (reason, action_url or (action.strip() if action else None), method)
        group = form_groups.get(key)
        if group is None:
            form_groups[key] = _FormGroup(
                reason=reason,
                page_url=page_url,
                count=1,
                action=action_url or action,
                method=method,
                response=response,
                tag=form.get("tag"),
            )
        else:
            group.count += 1
    for group in list(form_groups.values())[:MAX_FORM_FINDINGS]:
        findings.append(
            _broken_form_finding(
                reason=group.reason,
                page_url=group.page_url,
                page_count=group.count,
                action=group.action,
                method=group.method,
                response=group.response,
                tag=group.tag,
            )
        )
    return findings
