import type { Metadata } from "next";
import { Suspense } from "react";

import { RunPageContent } from "./run-page-content";

export const metadata: Metadata = {
  title: "Audit run",
};

// Not async: params are read inside the Suspense boundary, so the app shell
// stays in the static shell (cacheComponents) and no prerender error is logged.
export default function RunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<div aria-hidden="true" className="min-h-[60vh]" />}>
      <RunPageForParams params={params} />
    </Suspense>
  );
}

async function RunPageForParams({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RunPageContent runId={id} />;
}
