import { cn } from "@/lib/utils";

/**
 * Display-size LaunchAudit mark for the homepage hero.
 *
 * Same inspection tag as `LogoMark`, with one load-time sequence: a faint scan
 * line passes down the tag once, then the tick draws in. With reduced motion
 * the global rule in globals.css skips straight to the final frame (tick
 * drawn, scan line hidden).
 */
export function HeroMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      className={cn("shrink-0 overflow-visible", className)}
    >
      <defs>
        <clipPath id="hero-mark-tag">
          <path d="M4 3.5h11.2l4.8 4.8V20.5H4z" />
        </clipPath>
      </defs>
      <path d="M4 3.5h11.2l4.8 4.8V20.5H4z" className="fill-primary" />
      <g clipPath="url(#hero-mark-tag)">
        <rect
          data-part="scan"
          x="3"
          y="0"
          width="18"
          height="0.7"
          className="animate-hero-scan fill-primary-foreground opacity-0"
        />
      </g>
      <path
        d="M15.2 3.5v4.8H20"
        className="fill-none stroke-background"
        strokeWidth="1.5"
      />
      <path
        data-part="tick"
        d="m7.6 13.2 2.9 2.9 5.9-6.2"
        pathLength={1}
        strokeDasharray="1"
        className="animate-hero-tick fill-none stroke-primary-foreground"
        strokeWidth="2.2"
        strokeLinecap="square"
      />
    </svg>
  );
}
