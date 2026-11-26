"use client";


import { formatRiskScore, type Verdict } from "@/lib/report";
import { cn } from "@/lib/utils";

import { useCountUp } from "./use-count-up";

const RING_TONE: Record<Verdict, string> = {
  launch: "stroke-verdict-launch",
  fix_first: "stroke-verdict-fix",
  do_not_launch: "stroke-verdict-block",
};

/**
 * Risk score as a ring that fills while the number counts up. The visible
 * digits are aria-hidden; screen readers get "7.8 out of 10" once.
 */
export function ScoreRing({
  score,
  verdict,
  size = 168,
  className,
  label = "Risk score",
}: {
  score: number;
  verdict: Verdict | null;
  size?: number;
  className?: string;
  label?: string;
}) {
  const target = Math.min(10, Math.max(0, score));
  // Counts up from 0 once after mount; the server HTML already shows the final
  // value, and reduced motion jumps straight to it.
  const shown = useCountUp({ from: 0, to: target, durationMs: 900, delayMs: 200, start: true });

  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true" className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} className="stroke-muted" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          className={verdict ? RING_TONE[verdict] : "stroke-brand"}
          strokeDasharray={circumference}
          style={{ strokeDashoffset: circumference * (1 - shown / 10) }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span aria-hidden="true" className="font-display text-[2.75rem] leading-none font-semibold tracking-[-0.03em] tabular-nums">
          {formatRiskScore(shown)}
        </span>
        <span aria-hidden="true" className="mt-1 text-xs text-muted-foreground">
          out of 10
        </span>
        <span className="sr-only">
          {label}: {formatRiskScore(target)} out of 10
        </span>
      </div>
    </div>
  );
}
