import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Inline error panel for a failed data load. Distinct from EmptyState:
 * this is a failure with a retry, not an empty list. `actions` adds other
 * ways forward next to Try again.
 */
export function ErrorState({
  title,
  children,
  onRetry,
  actions,
  className,
}: {
  title: string;
  children: ReactNode;
  onRetry?: () => void;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <section
      role="alert"
      className={cn(
        "flex flex-col items-start gap-4 rounded-2xl border border-sev-critical/30 bg-card px-5 py-6 shadow-card sm:flex-row sm:px-6",
        className,
      )}
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-sev-critical-tint text-sev-critical">
        <TriangleAlert aria-hidden="true" className="size-5" />
      </span>
      <div className="flex min-w-0 flex-col gap-2">
        <h2 className="text-lg">{title}</h2>
        <div className="max-w-prose text-sm text-muted-foreground">{children}</div>
        {onRetry || actions ? (
          <div className="flex flex-wrap items-center gap-2 pt-2">
            {onRetry ? (
              <Button type="button" variant="outline" size="sm" onClick={onRetry}>
                Try again
              </Button>
            ) : null}
            {actions}
          </div>
        ) : null}
      </div>
    </section>
  );
}
