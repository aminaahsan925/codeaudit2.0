import { FileQuestion } from "lucide-react";
import type { Metadata } from "next";

import { ButtonLink } from "@/components/button-link";
import { AppShell } from "@/components/shell/app-shell";
import { StatusPage } from "@/components/shell/status-page";

export const metadata: Metadata = {
  title: "Page not found",
};

// Renders under the root layout only, so it brings the app shell itself.
export default function NotFound() {
  return (
    <AppShell>
      <StatusPage
        icon={FileQuestion}
        title="Page not found"
        actions={
          <>
            <ButtonLink href="/reports" size="lg">
              View reports
            </ButtonLink>
            <ButtonLink href="/audits/new" size="lg" variant="outline">
              Start a new audit
            </ButtonLink>
          </>
        }
      >
        <p>There is nothing at this address. The link may be old or mistyped.</p>
      </StatusPage>
    </AppShell>
  );
}
