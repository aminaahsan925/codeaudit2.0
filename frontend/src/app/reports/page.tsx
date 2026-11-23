import { ClipboardList } from "lucide-react";
import type { Metadata } from "next";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Reports",
};

export default function ReportsPage() {
  return (
    <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
      <PageHeader title="Reports">
        Every audit you run produces a Launch Report you can come back to.
      </PageHeader>
      <EmptyState
        icon={ClipboardList}
        title="No reports yet"
        actions={<ButtonLink href="/audits/new">Run an audit</ButtonLink>}
      >
        <p>
          Reports will be listed here once audits are available, each with its
          verdict, risk score and the proof behind every finding.
        </p>
      </EmptyState>
    </div>
  );
}
