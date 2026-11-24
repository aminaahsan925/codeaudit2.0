"use client";

import { FileSearch, Hourglass } from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { ReportView } from "@/components/report-view";
import { RunProgress } from "@/components/run-progress";
import { RunStatusBadge } from "@/components/run-status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApiError, Report } from "@/lib/api";
import { isActiveRunStatus } from "@/lib/report";

/**
 * Loading, error, not-finished and report states for a Launch Report page.
 * Shared by /reports/[id] and /r/[token]; only the query differs.
 */
export function ReportPageContent({
  query,
  readOnly = false,
}: {
  query: UseQueryResult<Report, ApiError>;
  /** True on the public shared report: findings show, but cannot be edited. */
  readOnly?: boolean;
}) {
  if (query.isPending) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Launch Report">Loading the report.</PageHeader>
        <div className="flex flex-col gap-6 rounded-xl border bg-card px-5 py-6 sm:px-8">
          <Skeleton className="h-8 w-56" />
          <Skeleton className="h-11 w-40" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    );
  }

  if (query.isError) {
    if (query.error.code === "not_found") {
      return (
        <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
          <PageHeader title="Launch Report" />
          <EmptyState
            icon={FileSearch}
            title="This report was not found"
            actions={<ButtonLink href="/audits/new">Run an audit</ButtonLink>}
          >
            <p>
              The link may be old or mistyped, or the report may have been
              removed. Start a new audit to get a fresh report.
            </p>
          </EmptyState>
        </div>
      );
    }
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Launch Report" />
        <ErrorState
          title="The report could not be loaded"
          onRetry={() => void query.refetch()}
        >
          <p>{query.error.message}</p>
        </ErrorState>
      </div>
    );
  }

  const report = query.data;
  if (!report) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title="Launch Report" />
        <EmptyState
          icon={FileSearch}
          title="This report was not found"
          actions={<ButtonLink href="/audits/new">Run an audit</ButtonLink>}
        >
          <p>The link may be old or mistyped. Start a new audit to get a fresh report.</p>
        </EmptyState>
      </div>
    );
  }

  const { run } = report;

  if (isActiveRunStatus(run.status)) {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title={`Launch Report: ${run.project_name}`}>
          This audit is still running. The report appears when it finishes.
        </PageHeader>
        <div className="flex flex-col gap-6 rounded-xl border bg-card px-5 py-6 sm:px-8">
          <RunStatusBadge status={run.status} />
          <RunProgress progress={run.progress} />
          <p>
            <ButtonLink href={`/audits/${run.id}`} variant="outline">
              Follow the audit
            </ButtonLink>
          </p>
        </div>
      </div>
    );
  }

  if (run.status === "failed") {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title={`Launch Report: ${run.project_name}`} />
        <ErrorState title="This audit failed, so there is no report">
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

  if (run.status === "cancelled") {
    return (
      <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
        <PageHeader title={`Launch Report: ${run.project_name}`} />
        <EmptyState
          icon={Hourglass}
          title="This audit was cancelled"
          actions={<ButtonLink href="/audits/new">Run a new audit</ButtonLink>}
        >
          <p>The audit stopped before it finished, so there is no report.</p>
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
      <ReportView report={report} readOnly={readOnly} />
    </div>
  );
}
