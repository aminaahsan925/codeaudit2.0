import type { Severity } from "@/lib/report";

/*
  Example findings for the homepage sample report. Each one carries the kind
  of proof a real Launch Report attaches: source with a flagged line and a
  data-flow trace, a live HTTP exchange, or response headers. Illustration
  only: nothing here is fetched or executed.
*/

export interface ProofLine {
  text: string;
  /** Marks the line that proves the finding. */
  flagged?: boolean;
}

export type Proof =
  | {
      kind: "code";
      file: string;
      firstLine: number;
      lines: readonly ProofLine[];
      trace: readonly { label: string; where: string }[];
    }
  | {
      kind: "http";
      request: readonly ProofLine[];
      response: readonly ProofLine[];
      note: string;
    }
  | {
      kind: "headers";
      request: string;
      headers: readonly ProofLine[];
      note: string;
    };

export interface SampleFinding {
  id: string;
  severity: Severity;
  title: string;
  source: string;
  proof: Proof;
}

export const SAMPLE_FINDINGS: readonly SampleFinding[] = [
  {
    id: "admin-key",
    severity: "critical",
    title: "Database admin key is shipped to the browser",
    source: "src/lib/db.ts, line 4",
    proof: {
      kind: "code",
      file: "src/lib/db.ts",
      firstLine: 1,
      lines: [
        { text: 'import { createClient } from "./supabase";' },
        { text: "" },
        { text: "const url = process.env.NEXT_PUBLIC_DB_URL!;" },
        { text: 'const adminKey = "sk_live_••••";', flagged: true },
        { text: "" },
        { text: "export const db = createClient(url, adminKey);" },
      ],
      trace: [
        { label: "Key defined", where: "src/lib/db.ts:4" },
        { label: "Passed to createClient", where: "src/lib/db.ts:6" },
        { label: "Imported by a client component", where: "src/app/notes/page.tsx:2" },
        { label: "Sent to every visitor", where: "notes page JavaScript bundle" },
      ],
    },
  },
  {
    id: "notes-access",
    severity: "high",
    title: "Any signed-in user can read other users’ notes",
    source: "Live request as a second test user",
    proof: {
      kind: "http",
      request: [
        { text: "GET /api/notes/1042" },
        { text: "Authorization: Bearer •••• (test user B)" },
      ],
      response: [
        { text: "HTTP/1.1 200 OK" },
        { text: "{" },
        { text: '  "id": 1042,' },
        { text: '  "owner": "test-user-a",', flagged: true },
        { text: '  "title": "Bank details"' },
        { text: "}" },
      ],
      note: "Note 1042 belongs to test user A. User B should get 403 or 404.",
    },
  },
  {
    id: "csp",
    severity: "medium",
    title: "Pages are served without a Content-Security-Policy",
    source: "Response headers from the live URL",
    proof: {
      kind: "headers",
      request: "GET https://pocket-notes.example.app/",
      headers: [
        { text: "content-type: text/html; charset=utf-8" },
        { text: "strict-transport-security: max-age=63072000" },
        { text: "x-content-type-options: nosniff" },
        { text: "content-security-policy: (missing)", flagged: true },
      ],
      note: "Without a CSP, any script injected into the page runs with full access to it.",
    },
  },
];
