import type { CSSProperties } from "react";

import { SeverityBadge, SeverityMark } from "@/components/severity-badge";
import { VerdictBadge } from "@/components/verdict-badge";
import { VERDICT_SUMMARY, formatRiskScore, type Severity } from "@/lib/report";
import {
  SAMPLE_FILE,
  SAMPLE_FINDINGS,
  SAMPLE_SCORE,
  SAMPLE_VERDICT,
  type SampleFinding,
} from "@/lib/sample-data";
import { cn } from "@/lib/utils";

/*
  The hero's example audit, built from the real badges and the one sample
  dataset. The sequence (scan line, flagged lines, findings, verdict) is plain
  CSS keyframes from tw-animate-css with per-element delays, so it needs no
  JavaScript and the server HTML is already the final frame for anyone without
  scripts. The global prefers-reduced-motion rule in globals.css zeroes every
  duration and delay, which renders the final frame straight away.
*/

const LINE_COUNT = SAMPLE_FILE.lines.length;
const SCAN_START = 300;
const SCAN_MS = 1700;
export const SCAN_END = SCAN_START + SCAN_MS;
export const VERDICT_AT = SCAN_END + 650;

/** The open findings tied to a line of the sample file, in list order. */
const HERO_FINDINGS = SAMPLE_FINDINGS.filter(
  (f): f is SampleFinding & { line: number } => !f.fixed && f.line !== undefined,
);

const FLAGGED = new Map(HERO_FINDINGS.map((f) => [f.line, f.severity]));

/** When the scan line passes a given (1-based) line. */
function lineAt(line: number): number {
  return SCAN_START + ((line - 0.4) / LINE_COUNT) * SCAN_MS;
}

function at(ms: number, duration?: number): CSSProperties {
  return {
    animationDelay: `${Math.round(ms)}ms`,
    ...(duration ? { animationDuration: `${duration}ms` } : {}),
  };
}

const LINE_TINT: Record<Severity, string> = {
  critical: "bg-sev-critical-tint",
  high: "bg-sev-high-tint",
  medium: "bg-sev-medium-tint",
  low: "bg-sev-low-tint",
};

const LINE_EDGE: Record<Severity, string> = {
  critical: "bg-sev-critical",
  high: "bg-sev-high",
  medium: "bg-sev-medium",
  low: "bg-sev-low",
};

const MARK_TONE: Record<Severity, string> = {
  critical: "[--mark:var(--sev-critical)]",
  high: "[--mark:var(--sev-high)]",
  medium: "[--mark:var(--sev-medium)]",
  low: "[--mark:var(--sev-low)]",
};

/** Strings get the brand ink so the code reads as code at a glance. */
function CodeText({ text }: { text: string }) {
  const parts = text.split(/("[^"]*")/g);
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith('"') ? (
          <span key={i} className="text-brand-fg">
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </>
  );
}

function CodePane() {
  return (
    <div className="border-b bg-sunken/70">
      <div className="flex h-10 items-center justify-between gap-3 px-4">
        <p className="truncate font-mono text-xs text-muted-foreground">{SAMPLE_FILE.path}</p>
        <div aria-hidden="true" className="grid shrink-0 text-xs font-medium">
          <span
            className="col-start-1 row-start-1 inline-flex items-center gap-1.5 text-brand-fg animate-out fade-out fill-mode-forwards"
            style={at(SCAN_END, 200)}
          >
            <span className="size-1.5 animate-pulse rounded-full bg-brand" />
            Reading your code
          </span>
          <span
            className="col-start-1 row-start-1 justify-self-end text-foreground animate-in fade-in fill-mode-both"
            style={at(SCAN_END + 150, 250)}
          >
            {HERO_FINDINGS.length} problems found
          </span>
        </div>
      </div>
      <div className="relative overflow-hidden pb-3" aria-hidden="true">
        <ol className="font-mono text-[0.75rem] leading-5">
          {SAMPLE_FILE.lines.map((text, index) => {
            const line = index + 1;
            const severity = FLAGGED.get(line);
            return (
              <li key={line} className="relative flex h-5 items-center pr-9">
                {severity && (
                  <>
                    <span
                      className={cn(
                        "absolute inset-0 animate-in fade-in fill-mode-both",
                        LINE_TINT[severity],
                      )}
                      style={at(lineAt(line), 260)}
                    />
                    <span
                      className={cn(
                        "absolute inset-y-0 left-0 w-0.5 animate-in fade-in fill-mode-both",
                        LINE_EDGE[severity],
                      )}
                      style={at(lineAt(line), 260)}
                    />
                  </>
                )}
                <span className="relative w-10 shrink-0 pr-4 text-right text-muted-foreground tabular-nums select-none">
                  {line}
                </span>
                <span className="relative min-w-0 truncate whitespace-pre text-foreground">
                  <CodeText text={text} />
                </span>
                {severity && (
                  <span
                    className={cn(
                      "absolute right-3 flex animate-in fade-in zoom-in-50 fill-mode-both",
                      MARK_TONE[severity],
                    )}
                    style={at(lineAt(line) + 60, 260)}
                  >
                    <SeverityMark severity={severity} />
                  </span>
                )}
              </li>
            );
          })}
        </ol>
        {/* The scan line: a full-height layer whose bottom edge is the line,
            swept from above the code to its bottom, then faded away. A flat
            tint one code line tall marks the line being read. */}
        <div className="pointer-events-none absolute inset-0 animate-out fade-out fill-mode-forwards" style={at(SCAN_END, 250)}>
          <div
            className="absolute inset-0 border-b-2 border-brand animate-in slide-in-from-top-full ease-linear fill-mode-both"
            style={at(SCAN_START, SCAN_MS)}
          >
            <div className="absolute inset-x-0 bottom-0 h-5 bg-brand/10" />
          </div>
        </div>
      </div>
    </div>
  );
}

/** The scanned file and the findings list: the part inside the browser frame. */
export function SampleReport({ className }: { className?: string }) {
  return (
    <div className={cn("bg-card text-card-foreground", className)}>
      <p className="sr-only">
        The example reads {SAMPLE_FILE.path} and flags {HERO_FINDINGS.length} lines.
      </p>
      <CodePane />
      <div className="px-3 pt-3 pb-4 sm:px-4">
        <h3 className="px-1 pb-2 font-sans text-xs font-medium tracking-normal text-muted-foreground">
          Fix first
        </h3>
        <ul className="flex flex-col gap-1.5">
          {HERO_FINDINGS.map((finding) => (
            <li
              key={finding.id}
              className="flex items-center gap-3 rounded-lg border bg-card px-3 py-2 shadow-xs animate-in fade-in zoom-in-95 slide-in-from-bottom-2 fill-mode-both ease-[cubic-bezier(0.22,1.2,0.36,1)]"
              style={at(lineAt(finding.line) + 140, 380)}
            >
              <SeverityBadge severity={finding.severity} className="w-[5.25rem] shrink-0" />
              <span className="min-w-0 truncate text-sm font-medium">{finding.plainTitle}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** The verdict moment: verdict, one sentence and the score. */
export function SampleVerdictCard({ className }: { className?: string }) {
  const size = 64;
  const stroke = 6;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const score = formatRiskScore(SAMPLE_SCORE);

  return (
    <div
      className={cn(
        "rounded-2xl border bg-card text-card-foreground shadow-float animate-in fade-in zoom-in-90 slide-in-from-bottom-4 fill-mode-both ease-[cubic-bezier(0.22,1.25,0.36,1)]",
        className,
      )}
      style={at(VERDICT_AT, 520)}
    >
      <div className="flex items-center gap-4 p-4">
        <div className="relative shrink-0" style={{ width: size, height: size }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true" className="-rotate-90">
            <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} className="stroke-muted" />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              strokeWidth={stroke}
              strokeLinecap="round"
              className="stroke-verdict-block"
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - SAMPLE_SCORE / 10)}
            />
          </svg>
          <span aria-hidden="true" className="absolute inset-0 flex items-center justify-center font-display text-xl font-semibold tabular-nums">
            {score}
          </span>
        </div>
        <div className="flex min-w-0 flex-col items-start gap-1.5">
          <VerdictBadge verdict={SAMPLE_VERDICT} />
          <p className="text-sm leading-snug">{VERDICT_SUMMARY[SAMPLE_VERDICT]}</p>
          <p className="sr-only">Risk score: {score} out of 10</p>
        </div>
      </div>
    </div>
  );
}
