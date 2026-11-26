import { RiskScore } from "@/components/risk-score";
import { SeverityBadge } from "@/components/severity-badge";
import { VerdictBadge } from "@/components/verdict-badge";
import { VERDICT_SUMMARY, type Severity } from "@/lib/report";
import { cn } from "@/lib/utils";

interface SampleFinding {
  severity: Severity;
  title: string;
  proofKind: string;
  proof: string;
}

const SAMPLE_FINDINGS: readonly SampleFinding[] = [
  {
    severity: "critical",
    title: "Database admin key is shipped to the browser",
    proofKind: "src/lib/db.ts, line 4",
    proof: 'const adminKey = "sk_live_••••";',
  },
  {
    severity: "high",
    title: "Any signed-in user can read other users’ notes",
    proofKind: "Live request as a second test user",
    proof: "GET /api/notes/1042  200 OK",
  },
  {
    severity: "medium",
    title: "Pages are served without a Content-Security-Policy",
    proofKind: "Response headers from the live URL",
    proof: "content-security-policy: (missing)",
  },
];

/**
 * A static, clearly labelled example of a Launch Report built from the real
 * badge components. It is illustration only: no data is fetched.
 */
export function SampleReport({ className }: { className?: string }) {
  return (
    <figure className={cn("relative", className)} aria-labelledby="sample-report-caption">
      <div
        aria-hidden="true"
        className="absolute inset-0 translate-x-2 translate-y-2 rounded-xl border bg-muted"
      />
      <div className="relative overflow-hidden rounded-xl border bg-card text-card-foreground">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b px-5 py-3">
          <div className="min-w-0">
            <p className="font-semibold">Launch Report for pocket-notes</p>
            <p className="truncate font-mono text-xs text-muted-foreground">
              pocket-notes.example.app
            </p>
          </div>
          <span className="rounded-sm border border-dashed border-input px-2 py-0.5 text-xs font-medium text-muted-foreground">
            Example
          </span>
        </div>

        <dl className="grid gap-5 border-b px-5 py-5 sm:grid-cols-[1fr_minmax(0,12rem)] sm:gap-8">
          <div className="flex flex-col gap-2">
            <dt className="text-sm text-muted-foreground">Verdict</dt>
            <dd className="flex flex-col items-start gap-2">
              <VerdictBadge verdict="do_not_launch" size="lg" />
              <span className="text-sm">{VERDICT_SUMMARY.do_not_launch}</span>
            </dd>
          </div>
          <div className="flex flex-col gap-2">
            <dt className="text-sm text-muted-foreground">Risk score</dt>
            <dd>
              <RiskScore score={7.8} />
            </dd>
          </div>
        </dl>

        <div className="px-5 pt-4 pb-5">
          <p className="mb-3 text-sm text-muted-foreground">
            3 findings, each with its proof
          </p>
          <ul className="flex flex-col divide-y">
            {SAMPLE_FINDINGS.map((finding) => (
              <li
                key={finding.title}
                className="grid gap-x-3 gap-y-1.5 py-3 first:pt-0 last:pb-0 sm:grid-cols-[5.75rem_1fr]"
              >
                <div>
                  <SeverityBadge severity={finding.severity} />
                </div>
                <div className="flex min-w-0 flex-col gap-1.5">
                  <p className="text-sm leading-snug font-semibold">{finding.title}</p>
                  <p className="text-xs text-muted-foreground">{finding.proofKind}</p>
                  <code className="block overflow-x-auto rounded-sm bg-muted px-2 py-1.5 font-mono text-xs whitespace-pre">
                    {finding.proof}
                  </code>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <figcaption
        id="sample-report-caption"
        className="relative mt-5 text-sm text-muted-foreground"
      >
        Example report for a fictional app. Your report lists every finding
        with the file, line or HTTP response that proves it.
      </figcaption>
    </figure>
  );
}
