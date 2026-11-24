import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Shared wrapper for the small line icons in this folder: 24x24, stroked
 * in the current text colour, decorative (the label beside the icon carries
 * the meaning).
 */
export function GraphicIcon({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={cn("size-6 shrink-0", className)}
    >
      {children}
    </svg>
  );
}
