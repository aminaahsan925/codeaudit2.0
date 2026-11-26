"use client";

import { ClipboardList, TriangleAlert } from "lucide-react";
import Link from "next/link";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { RunStatusBadge } from "@/components/run-status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { VerdictBadge } from "@/components/verdict-badge";
import { useRunsHistory, type HistoryEntry } from "@/hooks/use-runs-history";
import { formatDateTime } from "@/lib/dates";
import { isActiveRunStatus } from "@/lib/report";
import { removeStoredRun } from "@/lib/runs-history";

function HistoryRow({ entry }: { entry: HistoryEntry }) {
  const { stored, run, isLoading, isError } = entry;
  const date = formatDateTime(stored.createdAt);

  if (isError) {
    return (
      <li className="flex flex-col gap-3 rounded-lg border bg-card px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <p className="truncate text-base font-semibold">{stored.projectName}</p>
            {date ? (
              <p className="text-sm text-muted-foreground">{date}</p>
            ) : null}
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => removeStoredRun(stored.id)}
          >
            Remove from history
          </Button>
        </div>
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span>
            This run could not be loaded. It may have been removed, or the API
            may be unreachable.
          </span>
        </p>
      </li>
    );
  }

  if (isLoading || !run) {
    return (
      <li
        aria-label={`Loading ${stored.projectName}`}
        className="flex flex-col gap-3 rounded-lg border bg-card px-5 py-4"
      >
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-6 w-24" />
      </li>
    );
  }

  const href = run.status === "succeeded" ? `/reports/${run.id}` : `/audits/${run.id}`;
  const linkLabel =
    run.status === "succeeded"
      ? `View the Launch Report for ${stored.projectName}`
      : `Follow the audit for ${stored.projectName}`;

  return (
    <li className="rounded-lg border bg-card px-5 py-4 transition-colors hover:border-input">
      <Link
        href={href}
        aria-label={linkLabel}
        className="flex flex-col gap-3 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <p className="truncate text-base font-semibold">{stored.projectName}</p>
            {date ? (
              <p className="text-sm text-muted-foreground">{date}</p>
            ) : null}
          </div>
          <RunStatusBadge status={run.status} />
        </div>
        {run.status === "succeeded" && run.verdict && run.risk_score !== null ? (
          <div className="flex flex-wrap items-center gap-4">
            <VerdictBadge verdict={run.verdict} />
            <p className="font-mono text-sm text-muted-foreground">
              Risk score{" "}
              <span className="text-base font-semibold text-foreground">
                {run.risk_score.toFixed(1)}
              </span>
              <span aria-hidden="true"> / 10</span>
            </p>
          </div>
        ) : null}
        {isActiveRunStatus(run.status) ? (
          <p className="text-sm text-muted-foreground">
            {run.progress}% complete. Follow the audit to watch it finish.
          </p>
        ) : null}
        {run.status === "failed" ? (
          <p className="text-sm text-muted-foreground">
            This audit failed{run.error ? `: ${run.error}` : "."}
          </p>
        ) : null}
      </Link>
    </li>
  );
}

/**
 * Report history: the runs this browser created, newest first, each with
 * its live status. The list comes from localStorage because the API's run
 * list needs a bearer token and this build has no login; a run stays
 * reachable from its link on any device.
 */
export function ReportsHistory() {
  const { entries } = useRunsHistory();

  if (entries === null) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Reports">
          Every audit you run produces a Launch Report you can come back to.
        </PageHeader>
        <div className="flex flex-col gap-3" aria-label="Loading reports">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Reports">
          Every audit you run produces a Launch Report you can come back to.
        </PageHeader>
        <EmptyState
          icon={ClipboardList}
          title="No reports yet"
          actions={<ButtonLink href="/audits/new">Run an audit</ButtonLink>}
        >
          <p>
            Reports will be listed here once audits are available, each with its
            verdict, risk score and the proof behind every finding.
          </p>
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
      <PageHeader title="Reports">
        Every audit you run produces a Launch Report you can come back to.
      </PageHeader>
      <p className="-mt-4 max-w-prose text-sm text-muted-foreground">
        This list shows the audits run in this browser. A run stays reachable
        from its link on any device.
      </p>
      <ul className="flex flex-col gap-3">
        {entries.map((entry) => (
          <HistoryRow key={entry.stored.id} entry={entry} />
        ))}
      </ul>
    </div>
  );
}
