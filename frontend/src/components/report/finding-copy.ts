import type { Finding } from "@/lib/api";
import { plainTitleFor } from "@/lib/finding-titles";
import { CATEGORY_PLAIN } from "@/lib/glossary";

/**
 * The plain-English lead line for a finding, for example "Your database admin
 * key is visible to every visitor". The technical title is shown underneath.
 */
export function findingLead(
  finding: Pick<Finding, "rule_id" | "category" | "engine" | "title">,
): string {
  return plainTitleFor(finding);
}

/** "Exposed secret, CWE-798", or just the term when there is no CWE. */
export function findingTerm(finding: Pick<Finding, "category" | "cwe">): string {
  const { term } = CATEGORY_PLAIN[finding.category];
  return finding.cwe ? `${term}, ${finding.cwe}` : term;
}

/** "1 problem" / "3 problems". */
export function problemCount(n: number): string {
  return `${n} ${n === 1 ? "problem" : "problems"}`;
}
