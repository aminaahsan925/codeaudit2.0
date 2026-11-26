import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** A section's h2 and its one-line lead, on the left half of the grid. */
export function SectionIntro({
  id,
  title,
  children,
  className,
}: {
  id: string;
  title: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex max-w-2xl flex-col gap-4", className)}>
      <h2 id={id} className="text-3xl leading-[1.12] sm:text-[2.5rem]">
        {title}
      </h2>
      {children && <p className="text-lg text-muted-foreground">{children}</p>}
    </div>
  );
}
