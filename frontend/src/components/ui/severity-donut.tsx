"use client";

import * as m from "motion/react-m";

import { SeverityMark } from "@/components/severity-badge";
import { SEVERITIES, SEVERITY_LABEL, type Severity } from "@/lib/report";
import { cn } from "@/lib/utils";

import { EASE_OUT } from "./motion";

const ARC_TONE: Record<Severity, string> = {
  critical: "stroke-sev-critical",
  high: "stroke-sev-high",
  medium: "stroke-sev-medium",
  low: "stroke-sev-low",
};

/**
 * Open findings by severity: a small donut plus a legend that carries the
 * numbers in text, so the chart is never the only way to read them.
 */
export function SeverityDonut({
  counts,
  className,
}: {
  counts: Partial<Record<Severity, number>>;
  className?: string;
}) {
  const total = SEVERITIES.reduce((sum, s) => sum + (counts[s] ?? 0), 0);
  const size = 96;
  const stroke = 12;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const gap = total > 1 ? 3 : 0;

  const arcs = SEVERITIES.reduce<{ severity: Severity; length: number; offset: number }[]>(
    (acc, severity) => {
      const n = counts[severity] ?? 0;
      if (n === 0) return acc;
      const previous = acc[acc.length - 1];
      const offset = previous ? previous.offset + previous.length + gap : 0;
      const length = (n / total) * circumference;
      return [...acc, { severity, length: Math.max(0, length - gap), offset }];
    },
    [],
  );

  return (
    <div className={cn("flex items-center gap-5", className)}>
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true" className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} className="stroke-muted" />
          {arcs.map((arc, i) => (
            <m.circle
              key={arc.severity}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              strokeWidth={stroke}
              className={ARC_TONE[arc.severity]}
              strokeDasharray={`${arc.length} ${circumference}`}
              strokeDashoffset={-arc.offset}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, ease: EASE_OUT, delay: 0.3 + i * 0.08 }}
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl leading-none font-semibold tabular-nums">{total}</span>
          <span className="text-[0.6875rem] text-muted-foreground">open</span>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-5 gap-y-1.5 text-sm">
        {SEVERITIES.map((severity) => (
          <div key={severity} className="flex items-center gap-2">
            <dt className="flex items-center gap-1.5 text-muted-foreground">
              <SeverityMark severity={severity} className={cn("size-3", `[--mark:var(--sev-${severity})]`)} />
              {SEVERITY_LABEL[severity]}
            </dt>
            <dd className="font-semibold tabular-nums">{counts[severity] ?? 0}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
