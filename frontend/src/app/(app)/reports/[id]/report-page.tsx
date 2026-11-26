"use client";

import { ReportPageContent } from "@/components/report-page-content";
import { useReport } from "@/hooks/use-report";

/** The Launch Report for a run, resolved through the run's share token. */
export function ReportPage({ runId }: { runId: string }) {
  const query = useReport(runId);
  return <ReportPageContent query={query} />;
}
