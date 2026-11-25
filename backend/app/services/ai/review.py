"""AI review of findings: Gemini, then Groq, then rule-based.

Per finding, in order: Gemini if a Gemini key is configured, else Groq if
a Groq key is configured, else rule-based. A provider that errors, times
out (10s per call), or returns an unusable verdict falls through to the
next provider; when every provider fails, the finding gets rule-based
review. The model receives ONLY the masked snippet (max 500 chars),
file, line, rule id, and title, never full files.

The model must quote the exact code it refers to. The quote is verified
against the masked snippet (normalized whitespace); if it does not match,
the AI output is dropped and the finding gets rule-based review. Only
findings WITH a code snippet go to the model; live and journey findings
have no code to quote, so they get rule-based review directly.

A report is always produced: reviewing one finding never raises, and a
failure never stops the rest. API keys come from `Settings` only, never
from the environment, and are never logged.
"""

from __future__ import annotations

import json
import re

import httpx
from pydantic import SecretStr

from app.core.config import Settings
from app.schemas.finding import AIVerdict, AIVerdictLabel, Finding

from .rules import MAX_SNIPPET, rule_based_review

GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT = 10.0

AI_FIX_HEADING = "## AI suggested fix"
RULE_FIX_HEADING = "## Suggested fix"

_VERDICTS = {
    "confirmed": AIVerdictLabel.CONFIRMED,
    "likely false positive": AIVerdictLabel.LIKELY_FALSE_POSITIVE,
    "likely_false_positive": AIVerdictLabel.LIKELY_FALSE_POSITIVE,
    "needs review": AIVerdictLabel.NEEDS_REVIEW,
    "needs_review": AIVerdictLabel.NEEDS_REVIEW,
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def quote_matches(quote: str, snippet: str) -> bool:
    """True when the AI's quote appears in the (masked) snippet."""
    normalized_quote = _normalize(quote)
    if len(normalized_quote) < 8:
        return False
    return normalized_quote in _normalize(snippet)


def _parse_ai_json(text: str) -> dict | None:
    """Pull a JSON object out of an AI reply (fences tolerated)."""
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _prompt(finding: Finding) -> str:
    snippet = (finding.snippet or "")[:MAX_SNIPPET]
    where = ""
    if finding.file:
        where = f"{finding.file}:{finding.start_line}" if finding.start_line else finding.file
    return (
        "You review a pre-launch security finding. Reply with JSON only, "
        'no other text, using these keys: verdict ("confirmed" or '
        '"likely false positive"), explanation (one or two plain-English '
        "sentences), fixed_snippet (a short corrected code snippet), "
        "quote (the exact code from the snippet below that the finding "
        "refers to, copied word for word). "
        f"Rule: {finding.rule_id}. Title: {finding.title}. "
        f"Where: {where}. Code snippet:\n{snippet}"
    )


def _gemini_review(finding: Finding, api_key: str, client: httpx.Client) -> dict | None:
    try:
        response = client.post(
            GEMINI_URL,
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": _prompt(finding)}]}]},
        )
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        # Any provider error (network, HTTP status, bad payload) means the
        # next provider (or rule-based review) takes over. Nothing is
        # logged here: an exception could carry the request URL, which for
        # Gemini includes the API key.
        return None
    return _parse_ai_json(text)


def _groq_review(finding: Finding, api_key: str, client: httpx.Client) -> dict | None:
    try:
        response = client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": _prompt(finding)}],
                "temperature": 0,
            },
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
    except Exception:
        return None
    return _parse_ai_json(text)


def _key(value: SecretStr | None) -> str | None:
    if value is None:
        return None
    text = value.get_secret_value().strip()
    return text or None


def _usable_verdict(result: dict | None) -> AIVerdictLabel | None:
    """The verdict label a provider result carries, or None if unusable."""
    if not result:
        return None
    return _VERDICTS.get(str(result.get("verdict") or "").strip().lower())


def _provider_review(
    finding: Finding, settings: Settings, client: httpx.Client
) -> tuple[dict, AIVerdictLabel] | None:
    """Try each configured provider in order; None if none yields a verdict."""
    gemini_key = _key(settings.gemini_api_key)
    if gemini_key:
        result = _gemini_review(finding, gemini_key, client)
        verdict = _usable_verdict(result)
        if result is not None and verdict is not None:
            return result, verdict
    groq_key = _key(settings.groq_api_key)
    if groq_key:
        result = _groq_review(finding, groq_key, client)
        verdict = _usable_verdict(result)
        if result is not None and verdict is not None:
            return result, verdict
    return None


def _append_fix(finding: Finding, heading: str, snippet: str) -> None:
    block = f"{heading}\n\n```\n{snippet.strip()}\n```"
    existing = (finding.fix_guidance or "").rstrip()
    finding.fix_guidance = f"{existing}\n\n{block}" if existing else block


def _apply_rule_based(finding: Finding) -> None:
    verdict, fixed_snippet = rule_based_review(finding)
    finding.ai_verdict = verdict
    if fixed_snippet:
        _append_fix(finding, RULE_FIX_HEADING, fixed_snippet)


def _fallback_review(finding: Finding) -> None:
    """Last-resort review that cannot raise."""
    try:
        _apply_rule_based(finding)
    except Exception:
        finding.ai_verdict = AIVerdict(
            verdict=AIVerdictLabel.NEEDS_REVIEW,
            reason="This finding could not be reviewed automatically.",
            quoted_code="",
        )


def _review_one(finding: Finding, settings: Settings, client: httpx.Client) -> None:
    snippet = finding.snippet
    if not snippet:
        _apply_rule_based(finding)
        return
    reviewed = _provider_review(finding, settings, client)
    if reviewed is None:
        _apply_rule_based(finding)
        return
    result, verdict = reviewed
    quote = (result.get("quote") or "").strip()
    if not quote_matches(quote, snippet):
        # The model did not quote the exact code: drop its output.
        _apply_rule_based(finding)
        return
    reason = (result.get("explanation") or "").strip()
    if not reason:
        reason = rule_based_review(finding)[0].reason
    finding.ai_verdict = AIVerdict(verdict=verdict, reason=reason, quoted_code=quote)
    fixed = (result.get("fixed_snippet") or "").strip()
    if fixed:
        _append_fix(finding, AI_FIX_HEADING, fixed)


def review_findings(findings: list[Finding], settings: Settings) -> list[Finding]:
    """Set `ai_verdict` (and fix snippets) on every finding, in place.

    Returns the same list. A failure reviewing one finding never raises
    and never stops the rest; that finding gets rule-based review.
    """
    with httpx.Client(timeout=TIMEOUT, trust_env=False) as client:
        for finding in findings:
            try:
                _review_one(finding, settings, client)
            except Exception:
                _fallback_review(finding)
    return findings
