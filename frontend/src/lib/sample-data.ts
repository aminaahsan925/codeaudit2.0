import type { FindingCategory, Severity, Verdict } from "@/lib/report";

/*
  The one sample audit used across the marketing page: the hero product card,
  the example report preview and any other illustration. Change numbers here
  only, so every place agrees. Fictional app, fictional data.
*/

export interface SampleFinding {
  id: string;
  severity: Severity;
  category: FindingCategory;
  plainTitle: string;
  technicalTitle: string;
  cwe: string | null;
  where: string;
  /** Line of `SAMPLE_FILE.lines` (1-based) this finding flags, if any. */
  line?: number;
  proof: string;
  fixed?: boolean;
}

export const SAMPLE_PROJECT = {
  name: "pocket-notes",
  url: "pocket-notes.example.app",
  date: "26 Nov 2026",
} as const;

export const SAMPLE_VERDICT: Verdict = "do_not_launch";
export const SAMPLE_SCORE = 7.8;
export const SAMPLE_PREVIOUS_SCORE = 9.1;

export const SAMPLE_FILE = {
  path: "src/lib/notes.ts",
  lines: [
    'import { createClient } from "./supabase";',
    "",
    'const adminKey = "sk_live_••••••••";',
    "export const db = createClient(URL, adminKey);",
    "",
    "export async function getNote(id: string) {",
    '  return db.from("notes").select().eq("id", id);',
    "}",
    "",
    'export const cors = { origin: "*" };',
  ],
} as const;

export const SAMPLE_FINDINGS: readonly SampleFinding[] = [
  {
    id: "secret",
    severity: "critical",
    category: "secrets",
    plainTitle: "Your database admin key is visible to every visitor",
    technicalTitle: "Hard-coded secret shipped to the browser",
    cwe: "CWE-798",
    where: "src/lib/notes.ts:3",
    line: 3,
    proof: 'const adminKey = "sk_live_••••••••";',
  },
  {
    id: "access",
    severity: "high",
    category: "access_control",
    plainTitle: "Someone can read other users’ notes",
    technicalTitle: "Broken access control",
    cwe: "CWE-639",
    where: "GET /api/notes/1042",
    line: 7,
    proof: 'GET /api/notes/1042 as user B → 200 OK, "owner": "user-a"',
  },
  {
    id: "cors",
    severity: "medium",
    category: "config",
    plainTitle: "Any website can call your API from a visitor’s browser",
    technicalTitle: "Permissive CORS policy",
    cwe: "CWE-942",
    where: "src/lib/notes.ts:10",
    line: 10,
    proof: 'access-control-allow-origin: *',
  },
  {
    id: "debug",
    severity: "low",
    category: "config",
    plainTitle: "Debug mode was left on",
    technicalTitle: "Debug mode enabled in production",
    cwe: "CWE-489",
    where: "app.config.ts:21",
    proof: "DEBUG = true",
    fixed: true,
  },
];

/** Open findings by severity, derived so the counts can never disagree. */
export const SAMPLE_COUNTS: Record<Severity, number> = (["critical", "high", "medium", "low"] as const).reduce(
  (acc, severity) => {
    acc[severity] = SAMPLE_FINDINGS.filter((f) => f.severity === severity && !f.fixed).length;
    return acc;
  },
  { critical: 0, high: 0, medium: 0, low: 0 } as Record<Severity, number>,
);

export const SAMPLE_FIXED_COUNT = SAMPLE_FINDINGS.filter((f) => f.fixed).length;
export const SAMPLE_OPEN_COUNT = SAMPLE_FINDINGS.length - SAMPLE_FIXED_COUNT;
