import type { Metadata } from "next";

import { ReportPage } from "./report-page";

export const metadata: Metadata = {
  title: "Launch Report",
};

export default async function ReportRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ReportPage runId={id} />;
}
