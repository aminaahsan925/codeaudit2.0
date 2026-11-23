"""Tests for the AI review service (Gemini, Groq, rule-based fallback).

All provider calls go through httpx.MockTransport; no test touches the
network.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.schemas.finding import (
    AIVerdictLabel,
    Confidence,
    Finding,
    FindingCategory,
    FindingEngine,
    Severity,
)
from app.services.ai import review_findings
from app.services.ai.review import quote_matches
from app.services.ai.rules import DEFAULT_REVIEW, RULE_REVIEWS, rule_based_review

# Fake key-shaped value for tests only (not a real secret).
SNIPPET = 'API_KEY = "abcd1234efgh5678"'  # gitleaks:allow
BASE_GUIDANCE = "## Why it matters\n\nA secret in code is public.\n\n## How to fix\n\nMove it out."
GEMINI_KEY = "test-gemini-key"
GROQ_KEY = "test-groq-key"

Handler = Callable[[httpx.Request], httpx.Response]


def make_finding(**overrides: Any) -> Finding:
    values: dict[str, Any] = {
        "id": uuid4(),
        "rule_id": "SECRET_GENERIC",
        "engine": FindingEngine.NATIVE,
        "category": FindingCategory.SECRETS,
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "Hardcoded API key",
        "file": "app.py",
        "start_line": 3,
        "snippet": SNIPPET,
        "fix_guidance": BASE_GUIDANCE,
    }
    values.update(overrides)
    return Finding(**values)


def _ai_payload(
    *,
    verdict: str = "confirmed",
    quote: str = SNIPPET,
    explanation: str = "The key is hardcoded.",
    fixed_snippet: str = "API_KEY = os.environ.get('API_KEY')",
) -> dict[str, str]:
    return {
        "verdict": verdict,
        "explanation": explanation,
        "fixed_snippet": fixed_snippet,
        "quote": quote,
    }


def _gemini_response(payload: dict[str, str]) -> dict[str, Any]:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}


def _groq_response(payload: dict[str, str]) -> dict[str, Any]:
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


def _ok(body: dict[str, Any]) -> Handler:
    return lambda request: httpx.Response(200, json=body)


def _fail(status: int = 500) -> Handler:
    return lambda request: httpx.Response(status, json={"error": "boom"})


def _timeout() -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    return handler


def _explode() -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("boom")

    return handler


def _route(gemini: Handler | None = None, groq: Handler | None = None) -> Handler:
    """Route requests to per-provider handlers; None means "must not be called"."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "generativelanguage.googleapis.com" in url:
            assert gemini is not None, "Gemini should not have been called"
            return gemini(request)
        if "api.groq.com" in url:
            assert groq is not None, "Groq should not have been called"
            return groq(request)
        raise AssertionError(f"unexpected request to {url}")

    return handler


def _install_mock(
    monkeypatch: pytest.MonkeyPatch, handler: Handler, calls: list[httpx.Request]
) -> None:
    real_client = httpx.Client

    def recording_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    transport = httpx.MockTransport(recording_handler)
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: real_client(transport=transport))


def test_gemini_success_sets_verdict_and_appends_fix(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(gemini=_ok(_gemini_response(_ai_payload()))), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY, groq_api_key=GROQ_KEY)
    finding = make_finding()

    result = review_findings([finding], settings)

    assert result == [finding]
    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert finding.ai_verdict.reason == "The key is hardcoded."
    assert finding.ai_verdict.quoted_code == SNIPPET
    assert finding.fix_guidance is not None
    assert finding.fix_guidance.startswith(BASE_GUIDANCE)
    assert "## AI suggested fix" in finding.fix_guidance
    assert "API_KEY = os.environ.get('API_KEY')" in finding.fix_guidance
    # Gemini answered, so Groq was never tried.
    assert len(calls) == 1
    assert "generativelanguage.googleapis.com" in str(calls[0].url)


def test_gemini_failure_falls_back_to_groq(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    groq_payload = _ai_payload(
        verdict="likely false positive",
        explanation="This is a placeholder key.",
        fixed_snippet="",
    )
    _install_mock(
        monkeypatch,
        _route(gemini=_fail(), groq=_ok(_groq_response(groq_payload))),
        calls,
    )
    settings = settings_factory(gemini_api_key=GEMINI_KEY, groq_api_key=GROQ_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.LIKELY_FALSE_POSITIVE
    assert finding.ai_verdict.reason == "This is a placeholder key."
    assert len(calls) == 2


def test_both_providers_down_falls_back_to_rule_based(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(gemini=_fail(), groq=_fail()), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY, groq_api_key=GROQ_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert finding.ai_verdict.reason == RULE_REVIEWS["SECRET_GENERIC"].reason
    assert finding.ai_verdict.quoted_code == SNIPPET
    assert finding.fix_guidance is not None
    assert "## AI suggested fix" not in finding.fix_guidance
    assert "## Suggested fix" in finding.fix_guidance
    assert "os.environ.get('SECRET_KEY')" in finding.fix_guidance
    assert len(calls) == 2


def test_quote_mismatch_drops_ai_output(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    payload = _ai_payload(quote="totally different code here")
    _install_mock(monkeypatch, _route(gemini=_ok(_gemini_response(payload))), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY, groq_api_key=GROQ_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    # The quote did not match, so the AI output was dropped entirely:
    # rule-based review, and Groq was never tried.
    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert finding.ai_verdict.reason == RULE_REVIEWS["SECRET_GENERIC"].reason
    assert len(calls) == 1


def test_quote_too_short_to_verify_drops_ai_output(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    payload = _ai_payload(quote="x = 1")
    _install_mock(monkeypatch, _route(gemini=_ok(_gemini_response(payload))), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.reason == RULE_REVIEWS["SECRET_GENERIC"].reason


def test_findings_without_snippets_get_rule_based_review(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY, groq_api_key=GROQ_KEY)
    live = make_finding(
        rule_id="MISSING_SECURITY_HEADERS",
        engine=FindingEngine.LIVE,
        category=FindingCategory.CONFIG,
        severity=Severity.MEDIUM,
        title="Missing security headers",
        file=None,
        start_line=None,
        snippet=None,
    )
    journey = make_finding(
        rule_id="JOURNEY_STEP_FAILED",
        engine=FindingEngine.JOURNEY,
        category=FindingCategory.OTHER,
        severity=Severity.HIGH,
        title="Checkout fails at payment",
        file=None,
        start_line=None,
        snippet=None,
    )

    review_findings([live, journey], settings)

    assert live.ai_verdict is not None
    assert live.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert live.ai_verdict.reason == RULE_REVIEWS["MISSING_SECURITY_HEADERS"].reason
    assert live.ai_verdict.quoted_code == ""
    assert journey.ai_verdict is not None
    assert journey.ai_verdict.reason == RULE_REVIEWS["JOURNEY_STEP_FAILED"].reason
    # No code to quote, so no model was called.
    assert calls == []


def test_mixed_list_only_sends_snippet_findings_to_the_model(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(gemini=_ok(_gemini_response(_ai_payload()))), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY)
    code_finding = make_finding()
    live_finding = make_finding(
        rule_id="INSECURE_COOKIE",
        engine=FindingEngine.LIVE,
        category=FindingCategory.CONFIG,
        severity=Severity.MEDIUM,
        title="Insecure cookie",
        file=None,
        start_line=None,
        snippet=None,
    )

    review_findings([code_finding, live_finding], settings)

    assert len(calls) == 1
    assert live_finding.ai_verdict is not None
    assert live_finding.ai_verdict.reason == RULE_REVIEWS["INSECURE_COOKIE"].reason


def test_timeout_falls_back_to_rule_based(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(gemini=_timeout()), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert finding.ai_verdict.reason == RULE_REVIEWS["SECRET_GENERIC"].reason
    assert len(calls) == 1


def test_no_keys_goes_straight_to_rule_based(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(), calls)
    settings = settings_factory()
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert finding.ai_verdict.reason == RULE_REVIEWS["SECRET_GENERIC"].reason
    assert calls == []


def test_groq_used_when_only_groq_key_is_set(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(groq=_ok(_groq_response(_ai_payload()))), calls)
    settings = settings_factory(groq_api_key=GROQ_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert finding.ai_verdict.reason == "The key is hardcoded."
    assert len(calls) == 1
    assert "api.groq.com" in str(calls[0].url)


def test_invalid_verdict_falls_back_to_groq(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(
        monkeypatch,
        _route(
            gemini=_ok(_gemini_response(_ai_payload(verdict="maybe"))),
            groq=_ok(_groq_response(_ai_payload())),
        ),
        calls,
    )
    settings = settings_factory(gemini_api_key=GEMINI_KEY, groq_api_key=GROQ_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert len(calls) == 2


def test_needs_review_verdict_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    payload = _ai_payload(verdict="needs review", explanation="Not enough context.")
    _install_mock(monkeypatch, _route(gemini=_ok(_gemini_response(payload))), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.NEEDS_REVIEW
    assert finding.ai_verdict.reason == "Not enough context."


def test_ai_without_usable_snippet_leaves_fix_guidance_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    payload = _ai_payload(fixed_snippet="   ")
    _install_mock(monkeypatch, _route(gemini=_ok(_gemini_response(payload))), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY)
    finding = make_finding()

    review_findings([finding], settings)

    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.CONFIRMED
    assert finding.fix_guidance == BASE_GUIDANCE


def test_model_receives_only_the_masked_snippet(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(gemini=_ok(_gemini_response(_ai_payload()))), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY)
    long_snippet = "prefix " + "a" * 600 + " SECRET-MARKER"
    finding = make_finding(snippet=long_snippet)

    review_findings([finding], settings)

    assert len(calls) == 1
    body = json.loads(calls[0].content)
    prompt = body["contents"][0]["parts"][0]["text"]
    assert prompt.endswith(long_snippet[:500])
    assert "SECRET-MARKER" not in prompt


def test_review_never_raises_when_providers_explode(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    calls: list[httpx.Request] = []
    _install_mock(monkeypatch, _route(gemini=_explode(), groq=_explode()), calls)
    settings = settings_factory(gemini_api_key=GEMINI_KEY, groq_api_key=GROQ_KEY)
    findings = [make_finding(), make_finding(rule_id="DEBUG_MODE")]

    result = review_findings(findings, settings)

    assert result == findings
    assert all(f.ai_verdict is not None for f in findings)
    assert findings[0].ai_verdict is not None
    assert findings[0].ai_verdict.reason == RULE_REVIEWS["SECRET_GENERIC"].reason
    assert findings[1].ai_verdict is not None
    assert findings[1].ai_verdict.reason == RULE_REVIEWS["DEBUG_MODE"].reason


def test_review_never_raises_when_rule_based_fails(
    monkeypatch: pytest.MonkeyPatch,
    settings_factory: Callable[..., Settings],
) -> None:
    def _boom(finding: Finding) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("app.services.ai.review.rule_based_review", _boom)
    settings = settings_factory()
    finding = make_finding()

    result = review_findings([finding], settings)

    assert result == [finding]
    assert finding.ai_verdict is not None
    assert finding.ai_verdict.verdict == AIVerdictLabel.NEEDS_REVIEW


@pytest.mark.parametrize(
    "rule_id",
    [
        "SECRET_GENERIC",
        "SECRET_KNOWN_PREFIX",
        "HARDCODED_CREDENTIAL",
        "SECRET_GIT_HISTORY",
        "WEAK_PASSWORD_RULE",
        "DEBUG_MODE",
        "CORS_WILDCARD",
        "CORS_OPEN",
        "SQL_INJECTION",
        "XSS",
        "COMMAND_INJECTION",
        "WEAK_CRYPTO",
        "CVE_DEP",
        "SUPABASE_NO_RLS",
        "SUPABASE_SERVICE_KEY_FRONTEND",
        "SECRET_IN_PUBLIC_VAR",
        "FIREBASE_OPEN_RULES",
        "API_ROUTE_NO_AUTH",
        "LLM_KEY_FROM_BROWSER",
        "EXPOSED_ENV",
        "EXPOSED_GIT",
        "SECRETS_IN_JS_BUNDLE",
        "MISSING_SECURITY_HEADERS",
        "INSECURE_COOKIE",
        "OPEN_ADMIN_ROUTE",
        "JOURNEY_STEP_FAILED",
    ],
)
def test_rule_based_table_covers_rule(rule_id: str) -> None:
    finding = make_finding(rule_id=rule_id)
    template = RULE_REVIEWS[rule_id]

    verdict, fixed_snippet = rule_based_review(finding)

    assert verdict.verdict == AIVerdictLabel.CONFIRMED
    assert verdict.reason == template.reason
    assert verdict.reason
    assert verdict.quoted_code == SNIPPET
    assert fixed_snippet == template.fixed_snippet


def test_rule_based_review_falls_back_to_default_for_unknown_rules() -> None:
    finding = make_finding(rule_id="semgrep:python.lang.security.audit.dangerous-subprocess")

    verdict, fixed_snippet = rule_based_review(finding)

    assert verdict.verdict == AIVerdictLabel.CONFIRMED
    assert verdict.reason == DEFAULT_REVIEW.reason
    assert fixed_snippet is None


def test_journey_engine_always_gets_journey_template() -> None:
    finding = make_finding(
        rule_id="JOURNEY_STEP_FAILED",
        engine=FindingEngine.JOURNEY,
        snippet=None,
    )

    verdict, fixed_snippet = rule_based_review(finding)

    assert verdict.reason == RULE_REVIEWS["JOURNEY_STEP_FAILED"].reason
    assert verdict.quoted_code == ""
    assert fixed_snippet is None


def test_quote_matches_normalizes_whitespace() -> None:
    assert quote_matches(SNIPPET, SNIPPET)
    assert quote_matches('API_KEY   =\n  "abcd1234efgh5678"', SNIPPET)
    assert not quote_matches("something else entirely", SNIPPET)
    assert not quote_matches("short", SNIPPET)
    assert not quote_matches("", SNIPPET)
