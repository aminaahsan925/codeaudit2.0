import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Kbd({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <kbd
      className={cn(
        "inline-flex h-5 min-w-5 items-center justify-center rounded-[6px] border border-border bg-sunken px-1.5 font-sans text-xs leading-none font-medium text-muted-foreground",
        className,
      )}
    >
      {children}
    </kbd>
  );
}
