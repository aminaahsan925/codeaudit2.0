import { FileSearch } from "lucide-react";
import type { Metadata } from "next";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Page not found",
};

export default function NotFound() {
  return (
    <div className="container-page flex flex-col gap-8 py-10 sm:py-14">
      <PageHeader title="Page not found" />
      <EmptyState
        icon={FileSearch}
        title="There is nothing at this address"
        actions={
          <>
            <ButtonLink href="/">Go to home</ButtonLink>
            <ButtonLink href="/reports" variant="outline">
              View reports
            </ButtonLink>
          </>
        }
      >
        <p>The link may be old or mistyped. Check the address, or start again from the home page.</p>
      </EmptyState>
    </div>
  );
}
