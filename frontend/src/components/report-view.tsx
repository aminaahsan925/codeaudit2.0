import { CircleCheck, Download, FileSearch } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { FindingCard } from "@/components/finding-card";
import { JourneySteps } from "@/components/journey-steps";
import { RerunButton } from "@/components/rerun-button";
import { RiskScore } from "@/components/risk-score";
import { SeverityCounts } from "@/components/severity-counts";
import { ShareLink } from "@/components/share-link";
import { VerdictBadge } from "@/components/verdict-badge";
import { buttonVariants } from "@/components/ui/button";
import {
  reportPdfUrl,
  sharedReportPath,
  type Report,
} from "@/lib/api";
import { formatDateTime } from "@/lib/dates";
import { scoreChangeLabel, VERDICT_SUMMARY } from "@/lib/report";
import { cn } from "@/lib/utils";

/**
 * The full Launch Report, shared by /reports/[id] and /r/[token]:
 * verdict and risk score, severity counts, the fix-first findings list,
 * journey steps, and the rerun comparison when this run reran an earlier one.
 */
export function ReportView({
  report,
  readOnly = false,
}: {
  report: Report;
  /** True on the public shared report: findings show, but cannot be edited. */
  readOnly?: boolean;
}) {
  const {
    run,
    findings,
    counts,
    journey_steps,
    resolved_findings,
    score_change,
    previous_risk_score,
  } = report;
  const pdfUrl = reportPdfUrl(run.id, run.share_token);
  const changeLabel = scoreChangeLabel(
    score_change,
    previous_risk_score,
    run.risk_score,
  );
  const isRerun = run.previous_run_id !== null;
  const runDate = formatDateTime(run.finished_at ?? run.started_at);

  return (
    <div className="flex flex-col gap-10">
      <section
        aria-labelledby="report-summary"
        className="flex flex-col gap-6 rounded-xl border bg-card px-5 py-6 sm:px-8"
      >
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">
            Launch Report
            {runDate ? ` · ${runDate}` : ""}
          </p>
          <h1
            id="report-summary"
            className="text-3xl font-bold tracking-[-0.025em] text-balance"
          >
            {run.project_name}
          </h1>
          {run.live_url ? (
            <p className="truncate font-mono text-sm text-muted-foreground">
              {run.live_url}
            </p>
          ) : null}
        </div>

        <dl className="grid gap-6 sm:grid-cols-[1fr_minmax(0,12rem)] sm:gap-8">
          <div className="flex flex-col gap-2">
            <dt className="text-sm text-muted-foreground">Verdict</dt>
            <dd className="flex flex-col items-start gap-2">
              {run.verdict ? (
                <>
                  <VerdictBadge verdict={run.verdict} size="lg" />
                  <span className="text-sm">{VERDICT_SUMMARY[run.verdict]}</span>
                </>
              ) : (
                <span className="text-sm text-muted-foreground">
                  No verdict yet. The audit has not finished.
                </span>
              )}
            </dd>
          </div>
          <div className="flex flex-col gap-2">
            <dt className="text-sm text-muted-foreground">Risk score</dt>
            <dd>
              {run.risk_score !== null ? (
                <RiskScore score={run.risk_score} />
              ) : (
                <span className="text-sm text-muted-foreground">Not scored yet.</span>
              )}
            </dd>
          </div>
        </dl>

        <SeverityCounts counts={counts} />

        <div className="flex flex-col gap-4 border-t pt-5">
          <RerunButton runId={run.id} hasJourney={journey_steps.length > 0} />
          <div className="flex flex-wrap items-center gap-3">
            {pdfUrl ? (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noreferrer"
                className={cn(buttonVariants({ variant: "outline" }))}
              >
                <Download aria-hidden="true" className="size-4" />
                Download PDF
              </a>
            ) : null}
          </div>
          {run.share_token ? (
            <ShareLink path={sharedReportPath(run.share_token)} />
          ) : null}
        </div>
      </section>

      {isRerun ? (
        <section aria-labelledby="rerun-heading" className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h2 id="rerun-heading" className="text-xl font-semibold tracking-tight">
              Since the last run
            </h2>
            {changeLabel ? (
              <p className="max-w-prose text-sm text-muted-foreground">{changeLabel}</p>
            ) : null}
          </div>
          {resolved_findings.length > 0 ? (
            <div className="flex flex-col gap-3 rounded-lg border border-verdict-launch/45 bg-verdict-launch-tint/40 px-5 py-4">
              <p className="flex items-center gap-2 font-semibold">
                <CircleCheck aria-hidden="true" className="size-5 text-verdict-launch" />
                {resolved_findings.length}{" "}
                {resolved_findings.length === 1 ? "finding" : "findings"} resolved
              </p>
              <ul className="flex flex-col gap-1.5">
                {resolved_findings.map((finding) => (
                  <li key={finding.id} className="text-sm">
                    {finding.title}
                    {finding.file ? (
                      <span className="font-mono text-xs text-muted-foreground">
                        {" "}
                        · {finding.file}
                        {finding.start_line !== null ? `:${finding.start_line}` : ""}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="max-w-prose text-sm text-muted-foreground">
              Nothing from the last run is resolved yet. Everything below still
              needs fixing.
            </p>
          )}
        </section>
      ) : null}

      <section aria-labelledby="findings-heading" className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 id="findings-heading" className="text-xl font-semibold tracking-tight">
            What to fix first
          </h2>
          <p className="max-w-prose text-sm text-muted-foreground">
            {findings.length === 0
              ? "Nothing to fix."
              : `${findings.length} ${findings.length === 1 ? "finding" : "findings"}, most damaging first. Each one shows the proof behind it.`}
          </p>
        </div>
        {findings.length === 0 ? (
          <EmptyState icon={FileSearch} title="No problems found" headingLevel={3}>
            <p>
              The audit found nothing to fix in this run. The verdict and risk
              score above reflect that.
            </p>
          </EmptyState>
        ) : (
          <ol className="flex flex-col gap-3">
            {findings.map((finding, index) => (
              <FindingCard
                key={finding.id}
                finding={finding}
                index={index + 1}
                runId={run.id}
                shareToken={run.share_token ?? undefined}
                readOnly={readOnly}
              />
            ))}
          </ol>
        )}
      </section>

      <JourneySteps
        steps={journey_steps}
        runId={run.id}
        shareToken={run.share_token ?? undefined}
      />
    </div>
  );
}
