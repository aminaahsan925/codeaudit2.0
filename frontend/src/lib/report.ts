/*
  Display vocabulary for Launch Report values.

  The value unions mirror docs/api-contract.md (Finding.severity,
  AuditRun.verdict). Once the backend exposes these schemas in OpenAPI,
  derive the unions from @/types/api instead.
*/

export const SEVERITIES = ["critical", "high", "medium", "low"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const VERDICTS = ["launch", "fix_first", "do_not_launch"] as const;
export type Verdict = (typeof VERDICTS)[number];

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

/** Formats a 0-10 risk score with one decimal, clamped to the valid range. */
export function formatRiskScore(score: number): string {
  const clamped = Math.min(10, Math.max(0, score));
  return clamped.toFixed(1);
}
