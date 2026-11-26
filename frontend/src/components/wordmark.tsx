import Link from "next/link";

import { cn } from "@/lib/utils";

/** Mark: an inspection tag with a tick, drawn in the brand ink. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      className={cn("size-6 shrink-0", className)}
    >
      <path d="M5.5 2.5h9.7l4.3 4.3V19a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 3.5 19V4.5a2 2 0 0 1 2-2z" className="fill-brand" />
      <path d="M15.2 2.5v4.3h4.3" className="fill-none stroke-background" strokeWidth="1.4" strokeLinejoin="round" />
      <path
        d="m7.6 13.4 2.8 2.8 5.6-5.9"
        className="fill-none stroke-on-brand"
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "inline-flex items-center gap-2 rounded-md font-display text-[1.0625rem] font-semibold tracking-[-0.025em] text-foreground",
        className,
      )}
    >
      <LogoMark />
      <span>LaunchAudit</span>
    </Link>
  );
}
