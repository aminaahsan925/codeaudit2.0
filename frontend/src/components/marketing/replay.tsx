"use client";

import { RotateCcw } from "lucide-react";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Replays a CSS-animated sequence by remounting its children. The button is
 * hidden for reduced motion, where the sequence always shows its final frame.
 */
export function Replay({
  children,
  label,
  accessibleLabel,
  buttonClassName,
}: {
  children: ReactNode;
  label: string;
  /** Fuller name for screen readers; must start with the visible label. */
  accessibleLabel?: string;
  buttonClassName?: string;
}) {
  const [run, setRun] = useState(0);

  return (
    <>
      <div key={run} className="contents">
        {children}
      </div>
      <button
        type="button"
        aria-label={accessibleLabel}
        onClick={() => setRun((n) => n + 1)}
        className={cn(
          "inline-flex h-7 items-center gap-1.5 rounded-md px-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-card hover:text-foreground motion-reduce:hidden",
          buttonClassName,
        )}
      >
        <RotateCcw aria-hidden="true" className="size-3.5" />
        <span>{label}</span>
      </button>
    </>
  );
}
