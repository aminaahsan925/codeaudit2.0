import type { Metadata } from "next";

import { RunPageContent } from "./run-page-content";

export const metadata: Metadata = {
  title: "Audit run",
};

export default async function RunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <RunPageContent runId={id} />;
}
