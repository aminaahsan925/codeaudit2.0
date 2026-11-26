import type { FindingCategory, FindingEngine } from "@/lib/report";

/*
  Founder-facing titles. Each one says what can happen or what is exposed, in
  plain words, at most 70 characters. The technical title stays on the second
  line of a finding row.
*/

export interface TitledFinding {
  rule_id: string;
  category: FindingCategory;
  engine: FindingEngine;
  title: string;
}

/** Exact rule ids the scanner, live checks and journeys can emit. */
export const RULE_TITLES: Readonly<Record<string, string>> = {
  SECRET_GENERIC: "A secret value is written into your code",
  SECRET_KNOWN_PREFIX: "A live API key is written into your code",
  HARDCODED_CREDENTIAL: "A password is written into your code",
  SECRET_GIT_HISTORY: "A secret is still in your git history",
  WEAK_PASSWORD_RULE: "Users can pick very weak passwords",
  DEBUG_MODE: "Debug mode is on and can leak internal details",
  CORS_WILDCARD: "Any website can call your API from a visitor's browser",
  CORS_OPEN: "Any website can call your API from a visitor's browser",
  SQL_INJECTION: "Someone can type text that reads or changes your database",
  XSS: "Someone can run their own script in your users' browsers",
  COMMAND_INJECTION: "Someone can make your server run their commands",
  WEAK_CRYPTO: "Passwords or data are protected with a weak method",
  CVE_DEP: "A library you use has a known security bug",
  SUPABASE_NO_RLS: "Anyone can read or change your Supabase tables",
  SUPABASE_SERVICE_KEY_FRONTEND: "Your database admin key is visible to every visitor",
  SECRET_IN_PUBLIC_VAR: "A secret is exposed to every visitor's browser",
  FIREBASE_OPEN_RULES: "Anyone can read and write your Firebase data",
  API_ROUTE_NO_AUTH: "Anyone can call this API route without signing in",
  LLM_KEY_FROM_BROWSER: "Your AI provider key is visible to every visitor",
  EXPOSED_ENV: "Your .env file can be downloaded by anyone",
  EXPOSED_GIT: "Your source code history can be downloaded by anyone",
  SECRETS_IN_JS_BUNDLE: "A secret key is shipped inside your website's code",
  MISSING_SECURITY_HEADERS: "Your site is missing basic browser protections",
  INSECURE_COOKIE: "Sign-in cookies can be stolen or sent unprotected",
  OPEN_ADMIN_ROUTE: "Your admin page is open to anyone who finds it",
  JOURNEY_STEP_FAILED: "A step in your main user flow is broken",
};

const CATEGORY_TITLES: Readonly<Record<FindingCategory, string>> = {
  secrets: "A secret key is exposed in your code",
  injection: "Typed text can reach your database or server",
  auth: "Sign-in can be skipped or guessed",
  access_control: "Users can see data that belongs to others",
  config: "A risky setting is left on",
  dependency: "A library you use has a known security bug",
  ssrf: "Someone can make your server fetch any address",
  xss: "Someone can run their own script in your users' browsers",
  data_exposure: "Private data is sent where it should not go",
  other: "A security problem needs a look",
};

/** Plain title for a finding: exact rule, then engine pattern, then category. */
export function plainTitleFor(finding: TitledFinding): string {
  const exact = RULE_TITLES[finding.rule_id];
  if (exact) return exact;

  const id = finding.rule_id.toLowerCase();
  if (finding.engine === "gitleaks" || id.startsWith("gitleaks")) {
    return "A secret key is exposed in your code";
  }
  if (finding.engine === "osv" || id.startsWith("osv") || id.startsWith("pip-audit")) {
    return "A library you use has a known security bug";
  }
  return CATEGORY_TITLES[finding.category] ?? CATEGORY_TITLES.other;
}
