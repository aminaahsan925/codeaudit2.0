"""Speed and accessibility quick checks for the live home page.

Runs as part of the live-checks phase, after domain verification, through
the SSRF-safe client. No browser, no heavy dependency: speed is measured
with httpx timing on one extra GET of the home page, and accessibility is
checked by parsing the already-fetched home page HTML with stdlib
html.parser.

Speed thresholds (measured values are the proof, in the snippet and the
evidence notes):
  SLOW_TTFB  Medium over 800 ms, High over 2000 ms.
  SLOW_LOAD  Medium over 3000 ms, High over 8000 ms.
A page slower than the client's 10 s timeout cannot be measured at all:
the fetch times out and the speed check simply produces no findings.

Accessibility rules (all Low):
  IMG_MISSING_ALT     an <img> with no alt attribute. An empty alt ("")
                      counts as present: it marks a decorative image.
  INPUT_MISSING_LABEL an <input> with no label. Labelled means it has an
                      associated label[for], a wrapping <label>, an
                      aria-label, or an aria-labelledby. Inputs that need
                      no label are skipped: hidden, submit, button,
                      reset, and image, matching axe behaviour.
  MISSING_LANG        the <html> tag has no (non-empty) lang attribute.
  MISSING_TITLE       the page has no <title>, or it is empty.

Proof for the count-based rules is the count plus up to five examples.
Findings use category OTHER: the FindingCategory enum has no performance
or accessibility value, and adding one would be an API change.
"""

from __future__ import annotations

import contextlib
import uuid
from html.parser import HTMLParser

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

from .ssrf_client import SsrfBlockedError, SsrfSafeClient

# Time to first byte: Medium over 800 ms, High over 2000 ms.
TTFB_MEDIUM_MS = 800.0
TTFB_HIGH_MS = 2000.0

# Full load (whole body downloaded): Medium over 3000 ms, High over 8000 ms.
LOAD_MEDIUM_MS = 3000.0
LOAD_HIGH_MS = 8000.0

MAX_EXAMPLES = 5
MAX_EXAMPLE_LEN = 80

# Input types that never need a label (axe behaviour).
_NO_LABEL_INPUT_TYPES = frozenset({"hidden", "submit", "button", "reset", "image"})


def _severity_over(value_ms: float, medium_ms: float, high_ms: float) -> Severity | None:
    """Severity for a measured time, or None when it is fast enough."""
    if value_ms > high_ms:
        return Severity.HIGH
    if value_ms > medium_ms:
        return Severity.MEDIUM
    return None


def _truncate(text: str) -> str:
    if len(text) <= MAX_EXAMPLE_LEN:
        return text
    return text[: MAX_EXAMPLE_LEN - 1] + "..."


class _HomePageParser(HTMLParser):
    """Collect the accessibility facts of a home page.

    Label[for] associations are resolved after parsing, because a label
    may come after the input it labels.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_lang = False
        self.title_seen = False
        self._in_title = False
        self._title_parts: list[str] = []
        self.missing_alt_srcs: list[str] = []
        self._label_for_ids: set[str] = set()
        self._label_depth = 0
        self._inputs: list[dict[str, str | bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name: (value or "") for name, value in attrs}
        if tag == "html":
            if attrs_dict.get("lang", "").strip():
                self.has_lang = True
        elif tag == "title":
            self.title_seen = True
            self._in_title = True
        elif tag == "img":
            if "alt" not in attrs_dict:
                self.missing_alt_srcs.append(attrs_dict.get("src") or "(no src)")
        elif tag == "label":
            self._label_depth += 1
            label_for = attrs_dict.get("for", "")
            if label_for:
                self._label_for_ids.add(label_for)
        elif tag == "input":
            input_type = attrs_dict.get("type", "text").lower()
            if input_type in _NO_LABEL_INPUT_TYPES:
                return
            self._inputs.append(
                {
                    "id": attrs_dict.get("id", ""),
                    "name": attrs_dict.get("name", ""),
                    "type": input_type,
                    "aria": bool(
                        attrs_dict.get("aria-label", "").strip()
                        or attrs_dict.get("aria-labelledby", "").strip()
                    ),
                    "in_label": self._label_depth > 0,
                }
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "label":
            self._label_depth = max(0, self._label_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    @property
    def has_title(self) -> bool:
        return self.title_seen and bool("".join(self._title_parts).strip())

    def unlabelled_inputs(self) -> list[str]:
        """Human-readable examples of inputs with no label, e.g. "email (text)"."""
        examples: list[str] = []
        for entry in self._inputs:
            if entry["aria"] or entry["in_label"]:
                continue
            input_id = str(entry["id"])
            if input_id and input_id in self._label_for_ids:
                continue
            name = str(entry["name"])
            if name:
                ident = name
            elif input_id:
                ident = f"#{input_id}"
            else:
                ident = "(unnamed)"
            examples.append(f"{ident} ({entry['type']})")
        return examples


def _finding(
    *,
    rule_id: str,
    severity: Severity,
    title: str,
    why_it_matters: str,
    how_to_fix: str,
    snippet: str,
    notes: str,
    response: httpx.Response,
) -> Finding:
    return Finding(
        id=uuid.uuid4(),
        rule_id=rule_id,
        engine=FindingEngine.LIVE,
        category=FindingCategory.OTHER,
        severity=severity,
        confidence=Confidence.HIGH,
        title=title,
        snippet=snippet,
        evidence=Evidence(
            http=HttpEvidence(
                method=response.request.method,
                url=str(response.request.url),
                status=response.status_code,
            ),
            notes=notes,
        ),
        fix_guidance=(f"## Why it matters\n\n{why_it_matters}\n\n## How to fix\n\n{how_to_fix}"),
    )


def _examples_text(examples: list[str]) -> str:
    shown = [_truncate(example) for example in examples[:MAX_EXAMPLES]]
    return ", ".join(shown)


def check_speed(client: SsrfSafeClient, base_url: str) -> list[Finding]:
    """SLOW_TTFB / SLOW_LOAD: time one GET of the home page.

    A fast page produces no findings. Raises httpx.HTTPError (or
    SsrfBlockedError) when the page cannot be fetched; the caller decides
    what a failed measurement means.
    """
    timed = client.get_timed(base_url + "/")
    findings: list[Finding] = []
    ttfb_severity = _severity_over(timed.ttfb_ms, TTFB_MEDIUM_MS, TTFB_HIGH_MS)
    if ttfb_severity is not None:
        ttfb_ms = f"{timed.ttfb_ms:.0f}"
        findings.append(
            _finding(
                rule_id="SLOW_TTFB",
                severity=ttfb_severity,
                title="Slow time to first byte",
                why_it_matters=(
                    "The server took "
                    f"{ttfb_ms} ms to start answering. Every visitor waits "
                    "that long before anything can render, and slow servers "
                    "lose visitors before the page even starts."
                ),
                how_to_fix=(
                    "Find what the server waits on before responding: slow "
                    "database queries, uncached pages, or a server far from "
                    "your users. Cache the home page, speed up the slowest "
                    "query, and serve it from closer to your users."
                ),
                snippet=f"TTFB: {ttfb_ms} ms",
                notes=f"Path: /; TTFB {ttfb_ms} ms (over {TTFB_MEDIUM_MS:.0f} ms)",
                response=timed.response,
            )
        )
    load_severity = _severity_over(timed.load_ms, LOAD_MEDIUM_MS, LOAD_HIGH_MS)
    if load_severity is not None:
        load_ms = f"{timed.load_ms:.0f}"
        findings.append(
            _finding(
                rule_id="SLOW_LOAD",
                severity=load_severity,
                title="Slow page load",
                why_it_matters=(
                    "The home page took "
                    f"{load_ms} ms to download in full. Visitors on slow "
                    "connections wait that long for a complete page, and "
                    "many leave first."
                ),
                how_to_fix=(
                    "Shrink what the home page downloads: compress images, "
                    "drop scripts and styles the page does not use, and "
                    "enable compression on the server."
                ),
                snippet=f"Full load: {load_ms} ms",
                notes=f"Path: /; full load {load_ms} ms (over {LOAD_MEDIUM_MS:.0f} ms)",
                response=timed.response,
            )
        )
    return findings


def check_accessibility(home: httpx.Response) -> list[Finding]:
    """IMG_MISSING_ALT / INPUT_MISSING_LABEL / MISSING_LANG / MISSING_TITLE.

    Parses the already-fetched home page; a clean page produces no findings.
    """
    parser = _HomePageParser()
    parser.feed(home.text or "")
    parser.close()
    findings: list[Finding] = []

    if parser.missing_alt_srcs:
        count = len(parser.missing_alt_srcs)
        noun = "image" if count == 1 else "images"
        findings.append(
            _finding(
                rule_id="IMG_MISSING_ALT",
                severity=Severity.LOW,
                title="Images missing alt text",
                why_it_matters=(
                    "Screen readers skip images with no alt text, so blind "
                    "visitors miss whatever the image shows, and a broken "
                    "image leaves sighted visitors with nothing at all."
                ),
                how_to_fix=(
                    "Give every meaningful image a short alt attribute "
                    "describing what it shows. For purely decorative images, "
                    'use an empty alt (alt="") so screen readers skip them '
                    "on purpose."
                ),
                snippet=(
                    f"{count} {noun} missing alt text, e.g. "
                    f"{_examples_text(parser.missing_alt_srcs)}"
                ),
                notes=f"Path: /; {count} {noun} missing alt text",
                response=home,
            )
        )

    unlabelled = parser.unlabelled_inputs()
    if unlabelled:
        count = len(unlabelled)
        noun = "input" if count == 1 else "inputs"
        findings.append(
            _finding(
                rule_id="INPUT_MISSING_LABEL",
                severity=Severity.LOW,
                title="Form inputs missing labels",
                why_it_matters=(
                    "An input with no label is guesswork for screen reader "
                    "users and for anyone whose placeholder text disappears "
                    "as soon as they start typing."
                ),
                how_to_fix=(
                    'Label each input with a <label for="..."> matching '
                    "its id, wrap it in a <label>, or give it an aria-label."
                ),
                snippet=(f"{count} {noun} missing labels, e.g. {_examples_text(unlabelled)}"),
                notes=f"Path: /; {count} {noun} missing labels",
                response=home,
            )
        )

    if not parser.has_lang:
        findings.append(
            _finding(
                rule_id="MISSING_LANG",
                severity=Severity.LOW,
                title="Page has no language set",
                why_it_matters=(
                    "Without a lang attribute on <html>, screen readers "
                    "guess the language and often pronounce the page wrong, "
                    "and browsers cannot offer the right translation or "
                    "spellchecking."
                ),
                how_to_fix='Add the page language to the <html> tag, e.g. <html lang="en">.',
                snippet="<html> has no lang attribute",
                notes="Path: /",
                response=home,
            )
        )

    if not parser.has_title:
        title_snippet = (
            "page has no <title> element" if not parser.title_seen else "page <title> is empty"
        )
        findings.append(
            _finding(
                rule_id="MISSING_TITLE",
                severity=Severity.LOW,
                title="Page has no title",
                why_it_matters=(
                    "The <title> is what screen readers announce first, what "
                    "browser tabs show, and what search results display. "
                    "Without one, visitors cannot tell your page apart."
                ),
                how_to_fix=(
                    "Add a <title> inside <head> that names the page, e.g. "
                    "<title>Shop | Demo Store</title>."
                ),
                snippet=title_snippet,
                notes="Path: /",
                response=home,
            )
        )
    return findings


def check_speed_a11y(client: SsrfSafeClient, base_url: str, home: httpx.Response) -> list[Finding]:
    """Run the speed and accessibility quick checks on the home page.

    Accessibility parses the already-fetched home page, so it never needs
    the network again. Speed makes one extra timed fetch; if that fetch
    fails, the speed findings are dropped but the accessibility findings
    still stand.
    """
    findings = check_accessibility(home)
    with contextlib.suppress(httpx.HTTPError, SsrfBlockedError):
        findings.extend(check_speed(client, base_url))
    return findings
