import { cn } from "@/lib/utils";

/**
 * Hero illustration: a magnifier over a code window finds a leaked secret
 * (marked with the Critical octagon), and a shield with a check stands for
 * the verdict. Decorative; the headline and intro carry the meaning.
 * Colours come from the design tokens, so the illustration follows light
 * and dark mode.
 */
export function HeroIllustration({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 480 200"
      aria-hidden="true"
      focusable="false"
      className={cn("h-auto w-full", className)}
    >
      {/* Code window */}
      <rect
        x="8"
        y="30"
        width="252"
        height="132"
        rx="8"
        className="fill-card stroke-border"
        strokeWidth="1.5"
      />
      <line x1="8" y1="54" x2="260" y2="54" className="stroke-border" strokeWidth="1.5" />
      <circle cx="26" cy="42" r="4" className="fill-muted-foreground" opacity="0.5" />
      <circle cx="42" cy="42" r="4" className="fill-muted-foreground" opacity="0.5" />
      <circle cx="58" cy="42" r="4" className="fill-muted-foreground" opacity="0.5" />
      {/* Code lines */}
      <rect x="28" y="70" width="150" height="10" rx="3" className="fill-muted" />
      <rect x="28" y="90" width="196" height="10" rx="3" className="fill-muted" />
      <rect
        x="28"
        y="110"
        width="160"
        height="10"
        rx="3"
        className="fill-sev-critical-tint"
      />
      {/* Critical octagon on the leaked-secret line */}
      <polygon
        points="199,108 205,108 209,112 209,118 205,122 199,122 195,118 195,112"
        className="fill-sev-critical"
      />
      <rect x="28" y="130" width="120" height="10" rx="3" className="fill-muted" />
      {/* Magnifier */}
      <circle
        cx="292"
        cy="98"
        r="50"
        className="fill-card stroke-primary"
        fillOpacity="0.72"
        strokeWidth="6"
      />
      <rect x="266" y="78" width="52" height="8" rx="2" className="fill-primary" opacity="0.75" />
      <rect x="266" y="94" width="40" height="8" rx="2" className="fill-primary" opacity="0.75" />
      <rect x="266" y="110" width="30" height="8" rx="2" className="fill-primary" opacity="0.75" />
      <line
        x1="328"
        y1="134"
        x2="362"
        y2="168"
        className="stroke-primary"
        strokeWidth="9"
        strokeLinecap="round"
      />
      {/* Shield with a check: the verdict */}
      <path
        d="M424 58 L454 70 V94 C454 118 441 134 424 142 C407 134 394 118 394 94 V70 Z"
        className="fill-verdict-launch-tint stroke-verdict-launch"
        strokeWidth="3.5"
        strokeLinejoin="round"
      />
      <polyline
        points="411,96 421,106 438,86"
        fill="none"
        className="stroke-verdict-launch"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
