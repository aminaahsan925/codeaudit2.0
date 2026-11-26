"use client";

import { ReportPageContent } from "@/components/report-page-content";
import { useSharedReport } from "@/hooks/use-report";

/** The public shared report behind a share token. No account needed. Read only. */
export function SharedReportPage({ token }: { token: string }) {
  const query = useSharedReport(token);
  return <ReportPageContent query={query} readOnly />;
}
