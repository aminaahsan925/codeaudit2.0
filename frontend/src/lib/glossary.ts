import type { FindingCategory, Severity, Verdict } from "@/lib/report";

/*
  Plain-English copy for founders who are not security engineers. Lead with
  what can happen, then the technical name. Used by info tips and finding
  rows. Keep every entry to one or two short sentences.
*/

export interface TermExplanation {
  term: string;
  plain: string;
}

/** What each finding category means for the app's users. */
export const CATEGORY_PLAIN: Record<FindingCategory, TermExplanation> = {
  secrets: {
    term: "Exposed secret",
    plain: "A password or API key is visible to people who should not see it. Anyone who finds it can use it as you.",
  },
  injection: {
    term: "Injection",
    plain: "Text a user types can reach your database or server commands. An attacker can read or change data.",
  },
  auth: {
    term: "Broken authentication",
    plain: "Sign-in can be skipped or guessed, so someone can act as another user.",
  },
  access_control: {
    term: "Broken access control",
    plain: "A signed-in user can see or change data that belongs to someone else.",
  },
  config: {
    term: "Unsafe configuration",
    plain: "A setting is left in a risky state, like debug mode on or a missing security header.",
  },
  dependency: {
    term: "Vulnerable package",
    plain: "Your app uses a library with a known security bug. There is usually a fixed version.",
  },
  ssrf: {
    term: "Server-side request forgery",
    plain: "Someone can make your server fetch an address they choose, including internal ones.",
  },
  xss: {
    term: "Cross-site scripting",
    plain: "Someone can run their own script in your users' browsers, for example to steal sessions.",
  },
  data_exposure: {
    term: "Data exposure",
    plain: "Private data, like emails or tokens, is sent where it should not go.",
  },
  other: {
    term: "Other risk",
    plain: "A problem that does not fit the usual groups. The evidence shows what was found.",
  },
};

export const SEVERITY_PLAIN: Record<Severity, string> = {
  critical: "Fix before launch. Someone could take over accounts or data today.",
  high: "Fix before launch. A real attack path exists, with some effort.",
  medium: "Fix soon. It makes other attacks easier or leaks some information.",
  low: "Good to fix. Small risk on its own.",
};

export const VERDICT_PLAIN: Record<Verdict, string> = {
  launch: "No blocking problems found. You can launch, and keep an eye on the low items.",
  fix_first: "There are problems to fix before launch. None of them are emergencies.",
  do_not_launch: "Launching now would put your users or data at risk. Fix the critical items first.",
};

export const TERMS = {
  riskScore: {
    term: "Risk score",
    plain: "0 means nothing found, 10 means severe and easy to exploit. It goes down as you fix things.",
  },
  verdict: {
    term: "Verdict",
    plain: "Our launch recommendation, based on the most serious problems found.",
  },
  evidence: {
    term: "Evidence",
    plain: "The exact code line or web response that proves the problem is real.",
  },
  trace: {
    term: "Data-flow trace",
    plain: "The path the data takes through your code, step by step, from where it enters to where it causes harm.",
  },
  cwe: {
    term: "CWE",
    plain: "A standard ID for this kind of weakness. Useful when you search for fixes or talk to a security expert.",
  },
  domainToken: {
    term: "Domain verification",
    plain: "Proof that the site is yours, so we only test sites their owners asked us to test.",
  },
  journey: {
    term: "Test login journey",
    plain: "We sign up and log in as a test user to check pages behind the login, then forget the password.",
  },
} as const satisfies Record<string, TermExplanation>;
