import type { Metadata } from "next";

import { AuditForm } from "@/components/audit-form";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Run an audit",
};

export default function NewAuditPage() {
  return (
    <div className="container-page flex flex-col gap-8 py-8 sm:py-12">
      <PageHeader title="Run an audit">
        Four short steps. Only your code is required.
      </PageHeader>
      <AuditForm />
    </div>
  );
}
