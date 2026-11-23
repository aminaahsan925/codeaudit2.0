"use client";

import { CircleCheck, FileSearch, TriangleAlert } from "lucide-react";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { RunProgress } from "@/components/run-progress";
import { RunStatusBadge } from "@/components/run-status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRun } from "@/hooks/use-run";
import { isActiveRunStatus } from "@/lib/report";

/**
 * The run progress page: polls the run while it is queued or running, then
 * points at the report when it succeeds, or shows the failure message.
 */
export function RunPageContent({ runId }: { runId: string }) {
  const runQuery = useRun(runId);
  const run = runQuery.data;

  if (runQuery.isPending) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Audit run">
          Loading the run.
        </PageHeader>
        <div className="flex flex-col gap-4 rounded-xl border bg-card px-5 py-6 sm:px-8">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-2 w-full" />
        </div>
      </div>
    );
  }

  if (runQuery.isError) {
    if (runQuery.error.code === "not_found") {
      return (
        <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
          <PageHeader title="Audit run" />
          <EmptyState
            icon={FileSearch}
            title="This audit run was not found"
            actions={<ButtonLink href="/audits/new">Run an audit</ButtonLink>}
          >
            <p>
              The link may be old or mistyped, or the run may have been removed.
              Start a new audit to get a fresh link.
            </p>
          </EmptyState>
        </div>
      );
    }
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Audit run" />
        <ErrorState
          title="The run could not be loaded"
          onRetry={() => void runQuery.refetch()}
        >
          <p>{runQuery.error.message}</p>
        </ErrorState>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Audit run" />
        <EmptyState
          icon={FileSearch}
          title="This audit run was not found"
          actions={<ButtonLink href="/audits/new">Run an audit</ButtonLink>}
        >
          <p>The link may be old or mistyped. Start a new audit to get a fresh link.</p>
        </EmptyState>
      </div>
    );
  }

  if (isActiveRunStatus(run.status)) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title={`Audit: ${run.project_name}`}>
          The audit is running. This page updates on its own; there is no need
          to refresh it.
        </PageHeader>
        <div className="flex flex-col gap-6 rounded-xl border bg-card px-5 py-6 sm:px-8">
          <RunStatusBadge status={run.status} />
          <RunProgress progress={run.progress} />
          <p className="max-w-prose text-sm text-muted-foreground">
            LaunchAudit is reading the code and, when the domain is verified,
            probing the live app. A typical audit takes a few minutes. Keep
            this link: the report appears here when the audit finishes.
          </p>
        </div>
      </div>
    );
  }

  if (run.status === "succeeded") {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title={`Audit: ${run.project_name}`}>
          The audit finished. Your Launch Report is ready.
        </PageHeader>
        <EmptyState
          icon={CircleCheck}
          title="Audit complete"
          actions={
            <ButtonLink href={`/reports/${run.id}`} size="lg">
              View the Launch Report
            </ButtonLink>
          }
        >
          <p>
            The report has the verdict, the risk score and every problem with
            the proof behind it.
          </p>
        </EmptyState>
      </div>
    );
  }

  if (run.status === "failed") {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title={`Audit: ${run.project_name}`} />
        <ErrorState title="This audit failed">
          <p>
            {run.error ??
              "The audit could not finish. Check the repo URL or zip and try again."}
          </p>
          <p className="mt-2">
            <ButtonLink href="/audits/new" variant="outline" size="sm">
              Run a new audit
            </ButtonLink>
          </p>
        </ErrorState>
      </div>
    );
  }

  return (
    <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
      <PageHeader title={`Audit: ${run.project_name}`} />
      <EmptyState
        icon={TriangleAlert}
        title="This audit was cancelled"
        actions={<ButtonLink href="/audits/new">Run a new audit</ButtonLink>}
      >
        <p>The audit stopped before it finished, so there is no report.</p>
      </EmptyState>
    </div>
  );
}
