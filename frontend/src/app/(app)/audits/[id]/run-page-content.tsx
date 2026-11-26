"use client";

import { Clock, FileSearch, TriangleAlert } from "lucide-react";
import * as m from "motion/react-m";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { RunProgress } from "@/components/run-progress";
import { RunStatusBadge } from "@/components/run-status-badge";
import { popIn } from "@/components/ui/motion";
import { ScoreRing } from "@/components/ui/score-ring";
import { Skeleton } from "@/components/ui/skeleton";
import { VerdictBadge } from "@/components/verdict-badge";
import { useRun } from "@/hooks/use-run";
import type { AuditRun } from "@/lib/api";
import { formatDateTime } from "@/lib/dates";
import { VERDICT_PLAIN } from "@/lib/glossary";
import { isActiveRunStatus } from "@/lib/report";
import { cn } from "@/lib/utils";

import { RunPipeline } from "./run-pipeline";
import {
  SLOW_RUN_MS,
  findStage,
  formatDuration,
  getStages,
  msBetween,
  type StageView,
} from "./run-stages";

/** How long the finished verdict shows before the report opens on its own. */
export const AUTO_OPEN_DELAY_MS = 1_500;

/** Events that count as the person using the page, which stops the auto-open. */
const INTERACTION_EVENTS = ["pointerdown", "keydown", "focusin"] as const;

/** The current time, ticking every second while `live` is true. */
function useNow(live: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!live) return;
    const id = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(id);
  }, [live]);
  return now;
}

/**
 * Opens `href` after AUTO_OPEN_DELAY_MS unless the person clicks, presses a
 * key or moves focus first. It replaces the history entry, so Back skips
 * this page instead of landing on it and being sent forward again. With
 * reduced motion on, nothing animates but the report still opens.
 */
function useAutoOpen(href: string, enabled: boolean): boolean {
  const router = useRouter();
  const [stopped, setStopped] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    const stop = () => {
      cleanup();
      setStopped(true);
    };
    const timer = window.setTimeout(() => {
      cleanup();
      router.replace(href);
    }, AUTO_OPEN_DELAY_MS);
    function cleanup() {
      window.clearTimeout(timer);
      for (const name of INTERACTION_EVENTS) document.removeEventListener(name, stop, true);
    }
    for (const name of INTERACTION_EVENTS) document.addEventListener(name, stop, true);
    return cleanup;
  }, [enabled, href, router]);

  return enabled && !stopped;
}

function PageFrame({ children }: { children: ReactNode }) {
  return <div className="container-page flex flex-col gap-8 py-10 sm:py-14">{children}</div>;
}

/** Status, start time and duration under the page title. */
function RunMeta({ run, now }: { run: AuditRun; now: number }) {
  const started = formatDateTime(run.started_at);
  let duration: string | null = null;
  if (run.status === "running") {
    const ms = msBetween(run.started_at, now);
    duration = ms === null ? null : `Running for ${formatDuration(ms)}`;
  } else if (run.status === "succeeded" || run.status === "failed") {
    const ms = msBetween(run.started_at, run.finished_at);
    if (ms !== null) duration = `${run.status === "succeeded" ? "Took" : "Stopped after"} ${formatDuration(ms)}`;
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
      <RunStatusBadge status={run.status} />
      {run.status === "queued" ? <span>Waiting to start</span> : null}
      {started && run.started_at ? (
        <span>
          Started <time dateTime={run.started_at}>{started}</time>
        </span>
      ) : null}
      {duration ? <span className="tabular-nums">{duration}</span> : null}
    </div>
  );
}

function PipelineCard({
  stages,
  aside,
  className,
}: {
  stages: StageView[];
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-labelledby="run-stages-title"
      className={cn(
        "grid overflow-hidden rounded-2xl border bg-card shadow-card",
        aside ? "lg:grid-cols-[minmax(0,1fr)_19rem]" : "",
        className,
      )}
    >
      <div className="flex flex-col gap-5 px-5 py-6 sm:px-8 sm:py-7">
        <h2 id="run-stages-title" className="text-lg">
          What the audit does
        </h2>
        <RunPipeline stages={stages} />
      </div>
      {aside ? (
        <div className="order-first flex flex-col gap-6 border-b bg-sunken/60 px-5 py-6 sm:px-8 lg:order-none lg:border-b-0 lg:border-l lg:px-6 lg:py-7">
          {aside}
        </div>
      ) : null}
    </section>
  );
}

function ActiveRun({ run, stages, now }: { run: AuditRun; stages: StageView[]; now: number }) {
  const running = findStage(stages, "running");
  const elapsed = run.status === "running" ? msBetween(run.started_at, now) : null;
  const slow = elapsed !== null && elapsed >= SLOW_RUN_MS;

  return (
    <>
      {slow ? (
        <section
          aria-labelledby="run-slow-title"
          className="flex items-start gap-3 rounded-2xl border border-input bg-card px-5 py-4 shadow-card"
        >
          <Clock aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-brand" />
          <div className="flex flex-col gap-1">
            <h2 id="run-slow-title" className="text-base">
              Taking longer than usual
            </h2>
            <p className="max-w-prose text-sm text-muted-foreground">
              {running ? (
                <>
                  Still running: <span className="font-medium text-foreground">{running.label}</span>.{" "}
                </>
              ) : null}
              Large repos and slow live sites take longer.
            </p>
          </div>
        </section>
      ) : null}

      <PipelineCard
        stages={stages}
        aside={
          <>
            <RunProgress progress={run.progress} />
            <p className="text-sm text-muted-foreground">
              {running ? (
                <>
                  Now: <span className="font-medium text-foreground">{running.label}</span>
                </>
              ) : (
                "Waiting for the audit to start."
              )}
            </p>
            <p className="text-sm text-muted-foreground">
              Keep this link. The report opens here when the audit finishes, even if you close the
              page.
            </p>
          </>
        }
      />

      <p aria-live="polite" aria-atomic="true" className="sr-only">
        {running ? `${running.label}. ` : ""}
        {Math.round(run.progress)} percent complete.
      </p>
    </>
  );
}

function FinishedRun({ run, stages }: { run: AuditRun; stages: StageView[] }) {
  const href = `/reports/${run.id}`;
  const opening = useAutoOpen(href, true);

  return (
    <>
      <section
        aria-labelledby="run-done-title"
        className="flex flex-col gap-8 rounded-2xl border bg-card px-5 py-7 shadow-card sm:flex-row sm:items-center sm:px-8"
      >
        {run.risk_score !== null ? (
          <ScoreRing score={run.risk_score} verdict={run.verdict} size={132} className="shrink-0" />
        ) : null}
        <div className="flex min-w-0 flex-col items-start gap-4">
          <h2 id="run-done-title" className="text-xl">
            Audit complete
          </h2>
          {run.verdict ? (
            <m.div variants={popIn} initial="hidden" animate="show" className="flex flex-col gap-2">
              <VerdictBadge verdict={run.verdict} size="lg" />
              <p className="max-w-prose text-muted-foreground">{VERDICT_PLAIN[run.verdict]}</p>
            </m.div>
          ) : (
            <p className="max-w-prose text-muted-foreground">The report is ready.</p>
          )}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-1">
            <ButtonLink href={href} size="lg">
              Open the report
            </ButtonLink>
            <p aria-live="polite" className="text-sm text-muted-foreground">
              {opening ? "Opening the report. Click or press any key to stay here." : ""}
            </p>
          </div>
        </div>
      </section>
      <PipelineCard stages={stages} />
    </>
  );
}

function FailedRun({ run, stages }: { run: AuditRun; stages: StageView[] }) {
  const failed = findStage(stages, "failed");
  return (
    <>
      <ErrorState
        title="This audit failed"
        actions={
          <>
            <ButtonLink href="/audits/new" size="sm">
              Try again
            </ButtonLink>
            <ButtonLink href="/audits/new" variant="outline" size="sm">
              Edit the audit
            </ButtonLink>
          </>
        }
      >
        {failed ? (
          <p>
            It stopped at <span className="font-medium text-foreground">{failed.label}</span>.
          </p>
        ) : null}
        <p className="mt-1 text-foreground">
          {run.error ?? "The audit stopped before it finished, so there is no report."}
        </p>
        <p className="mt-1">
          {failed?.failureHint ?? "Check the repo URL or zip, then run the audit again."}
        </p>
      </ErrorState>
      <PipelineCard stages={stages} />
    </>
  );
}

function RunView({ run }: { run: AuditRun }) {
  const stages = getStages(run);
  const now = useNow(run.status === "running");
  const active = isActiveRunStatus(run.status);

  return (
    <PageFrame>
      <div className="flex flex-col gap-4">
        <PageHeader title={run.project_name}>
          {active ? "This page updates on its own while the audit runs. There is no need to refresh it." : null}
        </PageHeader>
        <RunMeta run={run} now={now} />
      </div>

      {active ? <ActiveRun run={run} stages={stages} now={now} /> : null}
      {run.status === "succeeded" ? <FinishedRun run={run} stages={stages} /> : null}
      {run.status === "failed" ? <FailedRun run={run} stages={stages} /> : null}
      {run.status === "cancelled" ? (
        <EmptyState
          icon={TriangleAlert}
          title="This audit was cancelled"
          actions={<ButtonLink href="/audits/new">Run a new audit</ButtonLink>}
        >
          <p>The audit stopped before it finished, so there is no report.</p>
        </EmptyState>
      ) : null}
    </PageFrame>
  );
}

function RunNotFound() {
  return (
    <PageFrame>
      <PageHeader title="Audit run" />
      <EmptyState
        icon={FileSearch}
        title="This audit run was not found"
        actions={<ButtonLink href="/audits/new">Run an audit</ButtonLink>}
      >
        <p>
          The link may be old or mistyped, or the run was removed. Start a new audit to get a fresh
          link.
        </p>
      </EmptyState>
    </PageFrame>
  );
}

/** Same footprint as the running view, so the page does not jump when data lands. */
function RunSkeleton() {
  return (
    <PageFrame>
      <div aria-busy="true" aria-label="Loading the audit run" className="flex flex-col gap-8">
        <div className="flex flex-col gap-4">
          <Skeleton className="h-10 w-72 max-w-full sm:h-11" />
          <Skeleton className="h-6 w-56" />
        </div>
        <div className="grid overflow-hidden rounded-2xl border bg-card shadow-card lg:grid-cols-[minmax(0,1fr)_19rem]">
          <div className="flex flex-col gap-6 px-5 py-6 sm:px-8 sm:py-7">
            <Skeleton className="h-6 w-48" />
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="flex gap-4">
                <Skeleton className="size-7 shrink-0 rounded-full" />
                <div className="flex flex-1 flex-col gap-2">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-4 w-full max-w-sm" />
                </div>
              </div>
            ))}
          </div>
          <div className="order-first flex flex-col gap-4 border-b bg-sunken/60 px-5 py-6 sm:px-8 lg:order-none lg:border-b-0 lg:border-l lg:px-6 lg:py-7">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-2 w-full" />
          </div>
        </div>
      </div>
    </PageFrame>
  );
}

/**
 * The run page: a live pipeline while the run is queued or running (the
 * hook polls every 2 seconds), the verdict when it succeeds, followed by
 * the report, and the failed stage with a way forward when it fails.
 */
export function RunPageContent({ runId }: { runId: string }) {
  const runQuery = useRun(runId);
  const run = runQuery.data;

  if (runQuery.isPending) return <RunSkeleton />;

  if (runQuery.isError) {
    if (runQuery.error.code === "not_found") return <RunNotFound />;
    return (
      <PageFrame>
        <PageHeader title="Audit run" />
        <ErrorState title="The run could not be loaded" onRetry={() => void runQuery.refetch()}>
          <p>{runQuery.error.message}</p>
        </ErrorState>
      </PageFrame>
    );
  }

  if (!run) return <RunNotFound />;

  return <RunView run={run} />;
}
