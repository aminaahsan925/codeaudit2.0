"use client";

import { FileSearch, Hourglass } from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { PageHeader } from "@/components/page-header";
import { REPORT_PAGE } from "@/components/report/layout";
import { ReportSkeleton } from "@/components/report/report-skeleton";
import { ReportView } from "@/components/report-view";
import { RunProgress } from "@/components/run-progress";
import { RunStatusBadge } from "@/components/run-status-badge";
import type { ApiError, Report } from "@/lib/api";
import { isActiveRunStatus } from "@/lib/report";

function StatePage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className={REPORT_PAGE}>
      <PageHeader title={title} />
      <div className="max-w-2xl">{children}</div>
    </div>
  );
}

function NotFound({ readOnly }: { readOnly: boolean }) {
  return (
    <StatePage title="Launch Report">
      <EmptyState
        icon={FileSearch}
        title="This report was not found"
        actions={
          <>
            <ButtonLink href="/audits/new">Run an audit</ButtonLink>
            {readOnly ? null : (
              <ButtonLink href="/reports" variant="outline">
                See your reports
              </ButtonLink>
            )}
          </>
        }
      >
        <p>
          The link may be old or mistyped, or the report may have been removed.
          Start a new audit to get a fresh report.
        </p>
      </EmptyState>
    </StatePage>
  );
}

/**
 * Loading, error, not-finished and report states for a Launch Report page.
 * Shared by /reports/[id] and /r/[token]; only the query differs.
 * `readOnly` is the shared view: no Rerun and no links to the owner's reports.
 */
export function ReportPageContent({
  query,
  readOnly = false,
}: {
  query: UseQueryResult<Report, ApiError>;
  readOnly?: boolean;
}) {
  if (query.isPending) {
    return <ReportSkeleton />;
  }

  if (query.isError) {
    if (query.error.code === "not_found") {
      return <NotFound readOnly={readOnly} />;
    }
    return (
      <StatePage title="Launch Report">
        <ErrorState
          title="The report could not be loaded"
          onRetry={() => void query.refetch()}
          actions={
            readOnly ? null : (
              <ButtonLink href="/reports" variant="ghost" size="sm">
                See your reports
              </ButtonLink>
            )
          }
        >
          <p>{query.error.message}</p>
        </ErrorState>
      </StatePage>
    );
  }

  const report = query.data;
  if (!report) {
    return <NotFound readOnly={readOnly} />;
  }

  const { run } = report;

  if (isActiveRunStatus(run.status)) {
    return (
      <div className={REPORT_PAGE}>
        <PageHeader title={`Launch Report: ${run.project_name}`}>
          This audit is still running. The report appears when it finishes.
        </PageHeader>
        <div className="flex max-w-2xl flex-col items-start gap-5 rounded-2xl border bg-card px-5 py-6 shadow-card sm:px-6">
          <RunStatusBadge status={run.status} />
          <RunProgress progress={run.progress} className="w-full" />
          <ButtonLink href={`/audits/${run.id}`} variant="outline">
            Follow the audit
          </ButtonLink>
        </div>
      </div>
    );
  }

  if (run.status === "failed") {
    return (
      <StatePage title={`Launch Report: ${run.project_name}`}>
        <ErrorState
          title="This audit failed, so there is no report"
          actions={
            <ButtonLink href="/audits/new" variant="outline" size="sm">
              Run a new audit
            </ButtonLink>
          }
        >
          <p>
            {run.error ??
              "The audit could not finish. Check the repo URL or zip and try again."}
          </p>
        </ErrorState>
      </StatePage>
    );
  }

  if (run.status === "cancelled") {
    return (
      <StatePage title={`Launch Report: ${run.project_name}`}>
        <EmptyState
          icon={Hourglass}
          title="This audit was cancelled"
          actions={<ButtonLink href="/audits/new">Run a new audit</ButtonLink>}
        >
          <p>The audit stopped before it finished, so there is no report.</p>
        </EmptyState>
      </StatePage>
    );
  }

  return <ReportView report={report} readOnly={readOnly} />;
}
