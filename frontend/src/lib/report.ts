/*
  Display vocabulary for Launch Report values.

  The value unions are derived from the generated OpenAPI types
  (src/types/api.ts); the labels are the display copy for them.
*/

import type { components } from "@/types/api";

export type Severity = components["schemas"]["Severity"];
export type Verdict = components["schemas"]["Verdict"];
export type AuditRunStatus = components["schemas"]["AuditRunStatus"];
export type FindingCategory = components["schemas"]["FindingCategory"];
export type FindingEngine = components["schemas"]["FindingEngine"];
export type Confidence = components["schemas"]["Confidence"];
export type AIVerdictLabel = components["schemas"]["AIVerdictLabel"];
export type JourneyStepStatus = "passed" | "failed" | "skipped";

export const SEVERITIES = ["critical", "high", "medium", "low"] as const satisfies readonly Severity[];

export const VERDICTS = ["launch", "fix_first", "do_not_launch"] as const satisfies readonly Verdict[];

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export const VERDICT_LABEL: Record<Verdict, string> = {
  launch: "Launch",
  fix_first: "Fix first",
  do_not_launch: "Do not launch",
};

export const VERDICT_SUMMARY: Record<Verdict, string> = {
  launch: "No blocking problems found.",
  fix_first: "Fix the listed problems before you launch.",
  do_not_launch: "Serious problems put users or data at risk.",
};

export const RUN_STATUS_LABEL: Record<AuditRunStatus, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Finished",
  failed: "Failed",
  cancelled: "Cancelled",
};

/** Statuses that still change: the run page polls while one of these holds. */
export function isActiveRunStatus(status: AuditRunStatus): boolean {
  return status === "queued" || status === "running";
}

export function isTerminalRunStatus(status: AuditRunStatus): boolean {
  return !isActiveRunStatus(status);
}

export const CATEGORY_LABEL: Record<FindingCategory, string> = {
  secrets: "Secrets",
  injection: "Injection",
  auth: "Auth",
  access_control: "Access control",
  config: "Config",
  dependency: "Dependency",
  ssrf: "SSRF",
  xss: "XSS",
  data_exposure: "Data exposure",
  other: "Other",
};

export const ENGINE_LABEL: Record<FindingEngine, string> = {
  native: "Built-in check",
  semgrep: "Semgrep",
  gitleaks: "Gitleaks",
  osv: "OSV",
  vibe: "Vibe check",
  live: "Live check",
  journey: "Journey",
  ai: "AI review",
};

export const CONFIDENCE_LABEL: Record<Confidence, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

export const AI_VERDICT_LABEL: Record<AIVerdictLabel, string> = {
  confirmed: "Confirmed",
  likely_false_positive: "Likely false positive",
  needs_review: "Needs review",
};

export const JOURNEY_STEP_STATUS_LABEL: Record<JourneyStepStatus, string> = {
  passed: "Passed",
  failed: "Failed",
  skipped: "Skipped",
};

/** Formats a 0-10 risk score with one decimal, clamped to the valid range. */
export function formatRiskScore(score: number): string {
  const clamped = Math.min(10, Math.max(0, score));
  return clamped.toFixed(1);
}

/**
 * Plain-language reading of a rerun score change (current minus previous,
 * so negative is an improvement). Null when there is no previous run.
 */
export function scoreChangeLabel(scoreChange: number | null): string | null {
  if (scoreChange === null) return null;
  if (scoreChange === 0) return "Risk score unchanged since the last run.";
  const magnitude = formatRiskScore(Math.abs(scoreChange));
  return scoreChange < 0
    ? `Risk score down ${magnitude} since the last run.`
    : `Risk score up ${magnitude} since the last run.`;
}
