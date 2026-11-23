import type { Metadata } from "next";

import { SharedReportPage } from "./shared-report-page";

export const metadata: Metadata = {
  title: "Shared Launch Report",
};

export default async function SharedReportRoute({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <SharedReportPage token={token} />;
}
