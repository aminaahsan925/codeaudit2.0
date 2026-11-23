import { Construction } from "lucide-react";
import type { Metadata } from "next";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Run an audit",
};

export default function NewAuditPage() {
  return (
    <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
      <PageHeader title="Run an audit">
        Add your code and your live URL, then press Run.
      </PageHeader>
      <EmptyState
        icon={Construction}
        title="Audit setup is not available yet"
        actions={
          <ButtonLink href="/" variant="outline">
            Back to home
          </ButtonLink>
        }
      >
        <p>
          This is where you will connect a GitHub repo or upload a zip, add the
          URL of your running app and start the audit. Until then, the API
          status in the header shows whether the LaunchAudit service is
          reachable.
        </p>
      </EmptyState>
    </div>
  );
}
