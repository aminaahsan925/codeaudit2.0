import Link from "next/link";

import { cn } from "@/lib/utils";

/** Mark: an inspection tag with a tick, drawn in the primary ink. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      className={cn("size-6 shrink-0", className)}
    >
      <path
        d="M4 3.5h11.2l4.8 4.8V20.5H4z"
        className="fill-primary"
      />
      <path d="M15.2 3.5v4.8H20" className="fill-none stroke-background" strokeWidth="1.5" />
      <path
        d="m7.6 13.2 2.9 2.9 5.9-6.2"
        className="fill-none stroke-primary-foreground"
        strokeWidth="2.2"
        strokeLinecap="square"
      />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "inline-flex items-center gap-2 rounded-sm text-lg font-bold tracking-[-0.02em] text-foreground",
        className,
      )}
    >
      <LogoMark />
      <span>LaunchAudit</span>
    </Link>
  );
}
