import type { Metadata } from "next";

import { AuditForm } from "@/components/audit-form";
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
      <AuditForm />
    </div>
  );
}
