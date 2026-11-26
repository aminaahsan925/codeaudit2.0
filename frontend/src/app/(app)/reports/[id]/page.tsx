import type { Metadata } from "next";
import { Suspense } from "react";

import { ReportSkeleton } from "@/components/report/report-skeleton";

import { ReportPage } from "./report-page";

export const metadata: Metadata = {
  title: "Launch Report",
};

// Not async: params are read inside the Suspense boundary, so the app shell
// and the report skeleton stay in the static shell (cacheComponents).
export default function ReportRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<ReportSkeleton />}>
      <ReportForParams params={params} />
    </Suspense>
  );
}

async function ReportForParams({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReportPage runId={id} />;
}
