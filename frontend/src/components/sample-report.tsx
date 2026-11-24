import { RiskScore } from "@/components/risk-score";
import { SampleFindings } from "@/components/sample-findings";
import { VerdictBadge } from "@/components/verdict-badge";
import { VERDICT_SUMMARY } from "@/lib/report";
import { SAMPLE_FINDINGS } from "@/lib/sample-report";
import { cn } from "@/lib/utils";

/**
 * A clearly labelled example of a Launch Report built from the real report
 * components. Findings open to show their proof. Illustration only: no data
 * is fetched.
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

        <div className="px-5 pt-4 pb-4">
          <p className="mb-2 text-sm text-muted-foreground">
            {SAMPLE_FINDINGS.length} findings. Open one to see its proof.
          </p>
          <SampleFindings />
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
