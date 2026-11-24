import type { AuditRun, Finding, Report } from "@/lib/api";

/** Test-only builders for API shapes. Not sample data shown to users. */

export const RUN_ID = "11111111-1111-4111-8111-111111111111";
export const PREVIOUS_RUN_ID = "22222222-2222-4222-8222-222222222222";
export const SHARE_TOKEN = "share-token-for-tests";

export function makeRun(overrides: Partial<AuditRun> = {}): AuditRun {
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
    journey_definition: null,
    previous_run_id: null,
    domain_verified: true,
    ...overrides,
  };
}

export function makeFinding(overrides: Partial<Finding> = {}): Finding {
  return {
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
    ...overrides,
  };
}

export function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    run: makeRun(),
    findings: [makeFinding()],
    counts: { critical: 1, high: 0, medium: 0, low: 0 },
    journey_steps: [],
    previous_risk_score: null,
    resolved_findings: [],
    score_change: null,
    ...overrides,
  };
}
