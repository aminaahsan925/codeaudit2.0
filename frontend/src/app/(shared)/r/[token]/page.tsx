import type { Metadata } from "next";
import { Suspense } from "react";

import { ReportSkeleton } from "@/components/report/report-skeleton";

import { SharedReportPage } from "./shared-report-page";

export const metadata: Metadata = {
  title: "Shared Launch Report",
};

// Not async: params are read inside the Suspense boundary, so the app shell
// and the report skeleton stay in the static shell (cacheComponents).
export default function SharedReportRoute({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  return (
    <Suspense fallback={<ReportSkeleton />}>
      <SharedReportForParams params={params} />
    </Suspense>
  );
}

async function SharedReportForParams({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <SharedReportPage token={token} />;
}
