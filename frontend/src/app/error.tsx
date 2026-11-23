"use client";

import { TriangleAlert } from "lucide-react";
import { useEffect } from "react";

import { ButtonLink } from "@/components/button-link";
import { EmptyState } from "@/components/empty-state";
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

  return (
    <div className="container-page py-10 sm:py-14">
      <EmptyState
        icon={TriangleAlert}
        title="This page failed to load"
        headingLevel={2}
        actions={
          <>
            <Button type="button" size="lg" onClick={() => retry()}>
              Try again
            </Button>
            <ButtonLink href="/" size="lg" variant="outline">
              Go to home
            </ButtonLink>
          </>
        }
      >
        <p role="alert">
          Something went wrong while rendering this page. Try again, and if it
          keeps failing, check that the LaunchAudit API is running.
        </p>
        {digest ? (
          <p className="mt-2 text-sm">
            Reference: <code className="font-mono">{digest}</code>
          </p>
        ) : null}
      </EmptyState>
    </div>
  );
}
