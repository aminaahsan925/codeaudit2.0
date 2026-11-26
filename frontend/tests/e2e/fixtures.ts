/** Test-only API payloads for the mocked backend. Not user-facing data. */

export const RUN_ID = "11111111-1111-4111-8111-111111111111";
export const NEW_RUN_ID = "99999999-9999-4999-8999-999999999999";
export const SHARE_TOKEN = "e2e-share-token";

export function runPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: RUN_ID,
    project_name: "pocket-notes",
    repo_url: "https://github.com/example/pocket-notes",
    live_url: "https://pocket-notes.example.app",
    status: "succeeded",
    progress: 100,
    verdict: "fix_first",
    risk_score: 4.3,
    started_at: "2026-11-24T00:00:00Z",
    finished_at: "2026-11-24T00:05:00Z",
    error: null,
    share_token: SHARE_TOKEN,
    is_guest: true,
    journey_steps: null,
    previous_run_id: null,
    domain_verified: true,
    ...overrides,
  };
}

export function reportPayload(overrides: Record<string, unknown> = {}) {
  return {
    run: runPayload(),
    findings: [
      {
        id: "33333333-3333-4333-8333-333333333333",
        rule_id: "SECRET_GENERIC",
        engine: "native",
        category: "secrets",
        severity: "critical",
        confidence: "high",
        cwe: "CWE-798",
        title: "Database admin key is shipped to the browser",
        file: "src/lib/db.ts",
        start_line: 4,
        end_line: 4,
        snippet: 'const adminKey = "sk_live_****";',
        trace: [],
        evidence: {},
        ai_verdict: null,
        fix_guidance:
          "## Why it matters\n\nA leaked key lets strangers read your data.\n\n## How to fix\n\nMove the key to an environment variable and rotate it.",
        status: "open",
      },
      {
        id: "44444444-4444-4444-8444-444444444444",
        rule_id: "MISSING_CSP",
        engine: "live",
        category: "config",
        severity: "medium",
        confidence: "high",
        cwe: null,
        title: "Pages are served without a Content-Security-Policy",
        file: null,
        start_line: null,
        end_line: null,
        snippet: null,
        trace: [],
        evidence: {
          http: {
            method: "GET",
            url: "https://pocket-notes.example.app/",
            status: 200,
            request_headers: {},
            response_headers: { "content-type": "text/html" },
            body_excerpt: null,
          },
          notes: "Path: /",
        },
        ai_verdict: null,
        fix_guidance:
          "## Why it matters\n\nWithout a CSP, injected scripts run freely.\n\n## How to fix\n\nServe a Content-Security-Policy header.",
        status: "open",
      },
    ],
    counts: { critical: 1, high: 0, medium: 1, low: 0 },
    journey_steps: [
      { name: "Sign up", status: "passed", screenshot_url: null, error: null },
      { name: "Check out", status: "failed", screenshot_url: null, error: "Payment failed." },
    ],
    previous_risk_score: null,
    resolved_findings: [],
    score_change: null,
    ...overrides,
  };
}
