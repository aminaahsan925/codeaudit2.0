"use client";

import { TriangleAlert } from "lucide-react";
import { useEffect } from "react";

import { ButtonLink } from "@/components/button-link";
import { AppShell } from "@/components/shell/app-shell";
import { StatusPage } from "@/components/shell/status-page";
import { Button } from "@/components/ui/button";

export default function RouteError({
  error,
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const digest =
    error instanceof Error && "digest" in error && typeof error.digest === "string"
      ? error.digest
      : null;

  // The root error boundary replaces the route group layout, so it renders
  // the app shell itself.
  return (
    <AppShell>
      <StatusPage
        icon={TriangleAlert}
        title="This page did not load"
        reference={digest}
        actions={
          <>
            <Button type="button" size="lg" onClick={() => retry()}>
              Try again
            </Button>
            <ButtonLink href="/reports" size="lg" variant="outline">
              View reports
            </ButtonLink>
          </>
        }
      >
        <p role="alert">
          Something broke while this page was loading. Try again. If it keeps
          failing, check that the LaunchAudit API is running.
        </p>
      </StatusPage>
    </AppShell>
  );
}
