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
        "flex flex-col items-start gap-5 rounded-2xl border bg-card px-6 py-10 shadow-card sm:px-10",
        className,
      )}
    >
      <span className="flex size-11 items-center justify-center rounded-xl bg-brand-soft text-brand-fg">
        <Icon aria-hidden="true" className="size-5" />
      </span>
      <div className="flex max-w-prose flex-col gap-2">
        <Heading className="text-xl">{title}</Heading>
        <div className="text-muted-foreground">{children}</div>
      </div>
      {actions ? <div className="flex flex-wrap gap-3 pt-1">{actions}</div> : null}
    </section>
  );
}
