import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Inline error panel for a failed data load. Distinct from EmptyState:
 * this is a failure with a retry, not an empty list.
 */
export function ErrorState({
  title,
  children,
  onRetry,
  className,
}: {
  title: string;
  children: ReactNode;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <section
      role="alert"
      className={cn(
        "flex flex-col items-start gap-3 rounded-lg border border-sev-critical/40 bg-sev-critical-tint/40 px-6 py-6",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <TriangleAlert aria-hidden="true" className="size-5 text-sev-critical" />
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      </div>
      <div className="max-w-prose text-sm text-muted-foreground">{children}</div>
      {onRetry ? (
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </section>
  );
}
