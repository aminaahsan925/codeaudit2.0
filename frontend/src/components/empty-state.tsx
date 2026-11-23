import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  children,
  actions,
  headingLevel = 2,
  className,
}: {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
  actions?: ReactNode;
  headingLevel?: 2 | 3;
  className?: string;
}) {
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <section
      className={cn(
        "flex flex-col items-start gap-4 rounded-lg border border-dashed border-input bg-card px-6 py-10 sm:px-10",
        className,
      )}
    >
      <span className="flex size-10 items-center justify-center rounded-md bg-muted text-muted-foreground">
        <Icon aria-hidden="true" className="size-5" />
      </span>
      <div className="flex max-w-prose flex-col gap-2">
        <Heading className="text-xl font-semibold tracking-tight">{title}</Heading>
        <div className="text-muted-foreground">{children}</div>
      </div>
      {actions ? <div className="flex flex-wrap gap-3 pt-2">{actions}</div> : null}
    </section>
  );
}
