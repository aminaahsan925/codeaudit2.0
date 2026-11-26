"use client";

import { ChevronRight, ClipboardList, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useId, type ReactNode } from "react";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { RunStatusBadge } from "@/components/run-status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { VerdictBadge } from "@/components/verdict-badge";
import { useRunsHistory, type HistoryEntry } from "@/hooks/use-runs-history";
import type { AuditRun } from "@/lib/api";
import { formatDateTime } from "@/lib/dates";
import { RUN_STATUS_LABEL, VERDICT_LABEL, formatRiskScore, isActiveRunStatus } from "@/lib/report";
import { removeStoredRun } from "@/lib/runs-history";
import { cn } from "@/lib/utils";

/*
  One grid for the header, rows and skeletons, so columns line up and a
  skeleton row is exactly as tall as the row that replaces it.
  Mobile, two lines:   name ............ status
                       verdict  score ... date
  From 768px, one line: name | verdict | score | date | status | chevron
*/
const ROW_GRID =
  "grid grid-cols-[minmax(0,1fr)_auto_auto] grid-rows-[auto_auto] items-center gap-x-3 gap-y-1.5 px-4 md:grid-cols-[minmax(0,1fr)_9.5rem_5.5rem_10.5rem_6.5rem_1rem] md:grid-rows-1 md:gap-x-5 md:px-5";
const ROW_HEIGHT = "h-[4.75rem] md:h-16";

const CELL = {
  name: "col-span-2 min-w-0 md:col-span-1",
  status: "col-start-3 row-start-1 justify-self-end md:col-start-5 md:justify-self-start",
  verdict: "col-start-1 row-start-2 min-w-0 md:col-start-2 md:row-start-1",
  score: "col-start-2 row-start-2 md:col-start-3 md:row-start-1",
  date: "col-start-3 row-start-2 justify-self-end md:col-start-4 md:row-start-1 md:justify-self-start",
  chevron: "hidden md:col-start-6 md:row-start-1 md:block",
} as const;

function DateCell({ iso }: { iso: string }) {
  const label = formatDateTime(iso);
  return (
    <span className={cn(CELL.date, "text-xs text-muted-foreground tabular-nums md:text-sm")}>
      {label ? <time dateTime={iso}>{label}</time> : null}
    </span>
  );
}

function VerdictCell({ run }: { run: AuditRun }) {
  if (run.status === "succeeded" && run.verdict) {
    return (
      <span className={CELL.verdict}>
        <VerdictBadge verdict={run.verdict} size="sm" />
      </span>
    );
  }
  let text = "No report";
  if (isActiveRunStatus(run.status)) text = `${Math.round(run.progress)}% complete`;
  return <span className={cn(CELL.verdict, "truncate text-sm text-muted-foreground")}>{text}</span>;
}

function ScoreCell({ run }: { run: AuditRun }) {
  if (run.status !== "succeeded" || run.risk_score === null) {
    return <span className={CELL.score} />;
  }
  return (
    <span className={cn(CELL.score, "text-sm tabular-nums")}>
      <span className="font-heading text-base font-semibold">{formatRiskScore(run.risk_score)}</span>
      <span className="text-muted-foreground"> / 10</span>
    </span>
  );
}

/** What a screen reader hears after the link name. */
function describeRun(run: AuditRun, date: string | null): string {
  const parts: string[] = [RUN_STATUS_LABEL[run.status]];
  if (run.status === "succeeded" && run.verdict) parts.push(`Verdict ${VERDICT_LABEL[run.verdict]}`);
  if (run.status === "succeeded" && run.risk_score !== null) {
    parts.push(`Risk score ${formatRiskScore(run.risk_score)} out of 10`);
  }
  if (isActiveRunStatus(run.status)) parts.push(`${Math.round(run.progress)} percent complete`);
  if (date) parts.push(date);
  return `${parts.join(". ")}.`;
}

function LoadedRow({ entry, run }: { entry: HistoryEntry; run: AuditRun }) {
  const { stored } = entry;
  const descriptionId = useId();
  const succeeded = run.status === "succeeded";
  const href = succeeded ? `/reports/${run.id}` : `/audits/${run.id}`;
  const label = succeeded
    ? `View the Launch Report for ${stored.projectName}`
    : `Follow the audit for ${stored.projectName}`;

  return (
    <li>
      <Link
        href={href}
        aria-label={label}
        aria-describedby={descriptionId}
        className={cn(
          ROW_GRID,
          ROW_HEIGHT,
          "group outline-none transition-colors hover:bg-sunken/70 focus-visible:bg-sunken/70 focus-visible:outline-2 focus-visible:outline-solid focus-visible:-outline-offset-2 focus-visible:outline-ring",
        )}
      >
        <span className={cn(CELL.name, "truncate font-medium")}>{stored.projectName}</span>
        <VerdictCell run={run} />
        <ScoreCell run={run} />
        <DateCell iso={stored.createdAt} />
        <span className={CELL.status}>
          <RunStatusBadge status={run.status} />
        </span>
        <ChevronRight
          aria-hidden="true"
          className={cn(
            CELL.chevron,
            "size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none",
          )}
        />
        <span id={descriptionId} className="sr-only">
          {describeRun(run, formatDateTime(stored.createdAt))}
        </span>
      </Link>
    </li>
  );
}

function UnloadableRow({ entry }: { entry: HistoryEntry }) {
  const { stored } = entry;
  return (
    <li className={cn(ROW_GRID, ROW_HEIGHT)}>
      <span className={cn(CELL.name, "truncate font-medium")}>{stored.projectName}</span>
      <p className="col-span-2 col-start-1 row-start-2 flex min-w-0 items-center gap-2 text-sm text-muted-foreground md:col-span-3 md:col-start-2 md:row-start-1">
        <TriangleAlert aria-hidden="true" className="size-4 shrink-0 text-sev-high" />
        <span className="truncate">This run could not be loaded.</span>
      </p>
      <span className={cn(CELL.status, "md:col-span-2 md:justify-self-end")}>
        <Button type="button" variant="ghost" size="sm" onClick={() => removeStoredRun(stored.id)}>
          Remove from history
        </Button>
      </span>
    </li>
  );
}

/** A row whose run is still loading: the stored name is known, the rest is not yet. */
function PendingRow({ name }: { name?: string }) {
  return (
    <li className={cn(ROW_GRID, ROW_HEIGHT)}>
      <div className={cn(CELL.name, "truncate font-medium")}>
        {name ?? <Skeleton className="h-5 w-40" />}
        {name ? <span className="sr-only">, loading</span> : null}
      </div>
      <div className={CELL.verdict}>
        <Skeleton className="h-6 w-24" />
      </div>
      <div className={CELL.score}>
        <Skeleton className="h-5 w-12" />
      </div>
      <div className={CELL.date}>
        <Skeleton className="h-4 w-28" />
      </div>
      <div className={CELL.status}>
        <Skeleton className="h-6 w-20" />
      </div>
    </li>
  );
}

function HistoryRow({ entry }: { entry: HistoryEntry }) {
  if (entry.isError) return <UnloadableRow entry={entry} />;
  if (entry.isLoading || !entry.run) return <PendingRow name={entry.stored.projectName} />;
  return <LoadedRow entry={entry} run={entry.run} />;
}

function ReportsTable({ children, busy = false }: { children: ReactNode; busy?: boolean }) {
  return (
    <div className="overflow-hidden rounded-2xl border bg-card shadow-card">
      <div
        aria-hidden="true"
        className={cn(
          ROW_GRID,
          "hidden h-10 border-b bg-sunken/60 text-xs font-medium text-muted-foreground md:grid",
        )}
      >
        <span>Project</span>
        <span>Verdict</span>
        <span>Risk score</span>
        <span>Date</span>
        <span>Status</span>
      </div>
      <ul aria-label="Reports" aria-busy={busy || undefined} className="divide-y">
        {children}
      </ul>
    </div>
  );
}

const INTRO = "Every audit you run produces a Launch Report you can come back to.";

/**
 * Report history: the runs this browser created, newest first, each with
 * its live status. The list comes from localStorage because the API's run
 * list needs a bearer token and this build has no login; a run stays
 * reachable from its link on any device.
 */
export function ReportsHistory() {
  const { entries } = useRunsHistory();

  if (entries !== null && entries.length === 0) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Reports">{INTRO}</PageHeader>
        <EmptyState
          icon={ClipboardList}
          title="No reports yet"
          actions={
            <>
              <ButtonLink href="/audits/new">Run an audit</ButtonLink>
              <ButtonLink href="/#example" variant="outline">
                See an example report
              </ButtonLink>
            </>
          }
        >
          <p>
            Each audit you run in this browser is listed here with its verdict, risk score and
            date.
          </p>
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <PageHeader title="Reports">{INTRO}</PageHeader>
        <ButtonLink href="/audits/new">Run an audit</ButtonLink>
      </div>
      <div className="flex flex-col gap-3">
        {entries === null ? (
          <ReportsTable busy>
            <PendingRow />
            <PendingRow />
            <PendingRow />
          </ReportsTable>
        ) : (
          <ReportsTable>
            {entries.map((entry) => (
              <HistoryRow key={entry.stored.id} entry={entry} />
            ))}
          </ReportsTable>
        )}
        <p className="max-w-prose text-sm text-muted-foreground">
          Only audits run in this browser are listed. Each run stays reachable from its link on any
          device.
        </p>
      </div>
    </div>
  );
}
