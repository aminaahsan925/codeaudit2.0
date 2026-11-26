import { CircleCheck } from "lucide-react";

import { JourneySteps } from "@/components/journey-steps";
import { problemCount } from "@/components/report/finding-copy";
import { FindingsList } from "@/components/report/findings-list";
import { FixedFindings } from "@/components/report/fixed-findings";
import { REPORT_ASIDE, REPORT_GRID, REPORT_PAGE } from "@/components/report/layout";
import { ReportActions } from "@/components/report/report-actions";
import { ReportHeader } from "@/components/report/report-header";
import { VerdictHero } from "@/components/report/verdict-hero";
import { reportPdfUrl, sharedReportPath, type Report } from "@/lib/api";

/**
 * The full Launch Report, shared by /reports/[id] and /r/[token].
 * Left (sticky on desktop): the verdict, risk score, open problems by
 * severity and the before and after of a rerun. Right: the action bar, the
 * fix-first list, what the rerun fixed, and the journey screenshots.
 * `readOnly` is the shared view: a read-only note, and "Run your own audit"
 * in place of Rerun.
 */
export function ReportView({
  report,
  readOnly = false,
}: {
  report: Report;
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
  const sharePath = run.share_token ? sharedReportPath(run.share_token) : null;
  const isRerun = run.previous_run_id !== null;

  return (
    <div className={REPORT_PAGE}>
      <ReportHeader run={run} readOnly={readOnly} />

      <div className={REPORT_GRID}>
        <div className={REPORT_ASIDE}>
          <VerdictHero
            verdict={run.verdict}
            riskScore={run.risk_score}
            counts={counts}
            isRerun={isRerun}
            previousRiskScore={previous_risk_score}
            scoreChange={score_change}
            fixedCount={resolved_findings.length}
          />
        </div>

        <div className="flex min-w-0 flex-col gap-8">
          <ReportActions
            runId={run.id}
            hasJourney={journey_steps.length > 0}
            pdfUrl={pdfUrl}
            sharePath={sharePath}
            readOnly={readOnly}
          />

          <section aria-labelledby="findings-heading" className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <h2 id="findings-heading" className="text-2xl">
                Fix these first
              </h2>
              <p className="max-w-prose text-sm text-muted-foreground">
                {findings.length === 0
                  ? "Nothing to fix."
                  : `${problemCount(findings.length)}, most serious first. Open one to see the proof and how to fix it.`}
              </p>
            </div>
            {findings.length === 0 ? (
              <div className="flex flex-col items-start gap-3 rounded-2xl border bg-card px-5 py-6 shadow-xs sm:flex-row sm:gap-4 sm:px-6">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-verdict-launch-tint text-verdict-launch">
                  <CircleCheck aria-hidden="true" className="size-5" />
                </span>
                <div className="flex max-w-prose flex-col gap-1">
                  <h3 className="text-lg">No problems found</h3>
                  <p className="text-sm text-muted-foreground">
                    The audit found nothing to fix in this run. The verdict and
                    risk score reflect that.
                  </p>
                </div>
              </div>
            ) : (
              <FindingsList findings={findings} runId={run.id} />
            )}
          </section>

          <FixedFindings findings={resolved_findings} />

          <JourneySteps steps={journey_steps} runId={run.id} liveUrl={run.live_url} />
        </div>
      </div>
    </div>
  );
}
