"use client";

import { Tabs } from "@base-ui/react/tabs";
import { CircleCheck } from "lucide-react";
import * as m from "motion/react-m";
import { useEffect, useRef, useState } from "react";

import { animateNumber, prefersReducedMotion } from "@/components/ui/use-count-up";

import { SeverityBadge } from "@/components/severity-badge";
import { InfoTip } from "@/components/ui/info-tip";
import { fadeRise } from "@/components/ui/motion";
import { SeverityDonut } from "@/components/ui/severity-donut";
import { VerdictBadge } from "@/components/verdict-badge";
import { CATEGORY_PLAIN, SEVERITY_PLAIN, TERMS, VERDICT_PLAIN } from "@/lib/glossary";
import { SEVERITY_LABEL, formatRiskScore, type Verdict } from "@/lib/report";
import {
  SAMPLE_COUNTS,
  SAMPLE_FINDINGS,
  SAMPLE_FIXED_COUNT,
  SAMPLE_PREVIOUS_SCORE,
  SAMPLE_PROJECT,
  SAMPLE_SCORE,
  SAMPLE_VERDICT,
  type SampleFinding,
} from "@/lib/sample-data";
import { cn } from "@/lib/utils";

function FixedChip() {
  return (
    <span className="inline-flex h-6 items-center gap-1 rounded-sm border border-verdict-launch/45 bg-verdict-launch-tint px-2 text-xs font-semibold text-verdict-launch-fg">
      <CircleCheck aria-hidden="true" className="size-3.5 text-verdict-launch" />
      Fixed
    </span>
  );
}

function FindingDetail({ finding }: { finding: SampleFinding }) {
  return (
    <m.div key={finding.id} variants={fadeRise} initial="hidden" animate="show" className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={finding.severity} />
        {finding.fixed && <FixedChip />}
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="text-xl leading-snug">{finding.plainTitle}</h3>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
          <span>{finding.technicalTitle}</span>
          {finding.cwe && (
            <span className="inline-flex items-center gap-1">
              <span className="font-medium text-foreground">{finding.cwe}</span>
              <InfoTip term={TERMS.cwe.term}>{TERMS.cwe.plain}</InfoTip>
            </span>
          )}
        </p>
      </div>
      <p>{CATEGORY_PLAIN[finding.category].plain}</p>
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3">
          <p className="flex items-center gap-1 text-sm font-medium">
            Proof
            <InfoTip term={TERMS.evidence.term}>{TERMS.evidence.plain}</InfoTip>
          </p>
          <p className="truncate font-mono text-xs text-muted-foreground">{finding.where}</p>
        </div>
        <pre className="overflow-x-auto rounded-xl border bg-sunken px-4 py-3 font-mono text-[0.8125rem] leading-6">
          <code>{finding.proof}</code>
        </pre>
      </div>
      <p className="rounded-xl bg-muted/60 px-4 py-3 text-sm">
        <span className="font-medium">{SEVERITY_LABEL[finding.severity]}.</span>{" "}
        <span className="text-muted-foreground">
          {finding.fixed
            ? "The rerun checked this again and the problem is gone."
            : SEVERITY_PLAIN[finding.severity]}
        </span>
      </p>
    </m.div>
  );
}

const RING_TONE: Record<Verdict, string> = {
  launch: "stroke-verdict-launch",
  fix_first: "stroke-verdict-fix",
  do_not_launch: "stroke-verdict-block",
};

const RING_SIZE = 116;
const RING_STROKE = 10;
const RING_RADIUS = (RING_SIZE - RING_STROKE) / 2;
const RING_LENGTH = 2 * Math.PI * RING_RADIUS;

/**
 * The example's risk score. It counts down from the previous score to the
 * current one in 0.6s, once the score block is fully in view, so the number
 * never disagrees with "Down from 9.1". The server HTML, reduced motion and a
 * ring already on screen at load all show the final score without counting.
 */
function PreviewScore() {
  const ref = useRef<HTMLDivElement>(null);
  const digitsRef = useRef<HTMLSpanElement>(null);
  const ringRef = useRef<SVGCircleElement>(null);

  // Server HTML and a ring already on screen show the final score. If the ring
  // starts off screen, it shows the previous score until it is fully in view,
  // then counts down once (0.6s). Values are written to the DOM directly so no
  // re-render runs per frame.
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined" || prefersReducedMotion()) return;
    const { top, bottom, height } = el.getBoundingClientRect();
    if (height === 0 || (bottom > 0 && top < window.innerHeight)) return;

    const paint = (value: number) => {
      if (digitsRef.current) digitsRef.current.textContent = formatRiskScore(value);
      if (ringRef.current) ringRef.current.style.strokeDashoffset = String(RING_LENGTH * (1 - value / 10));
    };
    paint(SAMPLE_PREVIOUS_SCORE);

    let cancel = () => {};
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.intersectionRatio >= 0.99)) {
          io.disconnect();
          cancel = animateNumber(SAMPLE_PREVIOUS_SCORE, SAMPLE_SCORE, 600, paint);
        }
      },
      { threshold: [0.99] },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancel();
    };
  }, []);

  return (
    <div ref={ref} className="flex items-center gap-5">
      <div className="relative inline-flex shrink-0 items-center justify-center" style={{ width: RING_SIZE, height: RING_SIZE }}>
        <svg width={RING_SIZE} height={RING_SIZE} viewBox={`0 0 ${RING_SIZE} ${RING_SIZE}`} aria-hidden="true" className="-rotate-90">
          <circle cx={RING_SIZE / 2} cy={RING_SIZE / 2} r={RING_RADIUS} fill="none" strokeWidth={RING_STROKE} className="stroke-muted" />
          <circle
            ref={ringRef}
            cx={RING_SIZE / 2}
            cy={RING_SIZE / 2}
            r={RING_RADIUS}
            fill="none"
            strokeWidth={RING_STROKE}
            strokeLinecap="round"
            className={RING_TONE[SAMPLE_VERDICT]}
            strokeDasharray={RING_LENGTH}
            style={{ strokeDashoffset: RING_LENGTH * (1 - SAMPLE_SCORE / 10) }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span ref={digitsRef} aria-hidden="true" className="font-display text-[2.25rem] leading-none font-semibold tracking-[-0.03em] tabular-nums">
            {formatRiskScore(SAMPLE_SCORE)}
          </span>
          <span aria-hidden="true" className="mt-1 text-xs text-muted-foreground">
            out of 10
          </span>
          <span className="sr-only">Risk score: {formatRiskScore(SAMPLE_SCORE)} out of 10</span>
        </div>
      </div>
      <div className="flex flex-col gap-1 text-sm">
        <p className="flex items-center gap-1 font-medium">
          Risk score
          <InfoTip term={TERMS.riskScore.term}>{TERMS.riskScore.plain}</InfoTip>
        </p>
        <p className="text-muted-foreground">
          Down from {formatRiskScore(SAMPLE_PREVIOUS_SCORE)} after {SAMPLE_FIXED_COUNT}{" "}
          {SAMPLE_FIXED_COUNT === 1 ? "fix" : "fixes"}.
        </p>
      </div>
    </div>
  );
}

/**
 * A clickable example report built from the sample dataset. Findings are
 * tabs (arrow keys move between them); the proof shows in the panel.
 */
export function ReportPreview() {
  const [selected, setSelected] = useState<string>(SAMPLE_FINDINGS[0]?.id ?? "");

  return (
    <div className="overflow-hidden rounded-[20px] border bg-card shadow-float">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b px-5 py-4 sm:px-6">
        <div className="min-w-0">
          <p className="font-display text-lg font-semibold tracking-[-0.02em]">
            Launch Report for {SAMPLE_PROJECT.name}
          </p>
          <p className="truncate text-sm text-muted-foreground">
            {SAMPLE_PROJECT.url}, checked {SAMPLE_PROJECT.date}
          </p>
        </div>
        <span className="rounded-md border border-dashed border-input px-2 py-0.5 text-xs font-medium text-muted-foreground">
          Example
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12">
        <div className="flex flex-col gap-6 border-b bg-sunken/50 p-5 sm:p-6 lg:col-span-4 lg:border-r lg:border-b-0">
          <div className="flex flex-col items-start gap-2">
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              Verdict
              <InfoTip term={TERMS.verdict.term}>{TERMS.verdict.plain}</InfoTip>
            </p>
            <VerdictBadge verdict={SAMPLE_VERDICT} size="lg" />
            <p className="text-sm">{VERDICT_PLAIN[SAMPLE_VERDICT]}</p>
          </div>
          <PreviewScore />
          <SeverityDonut counts={SAMPLE_COUNTS} />
        </div>

        <Tabs.Root
          value={selected}
          onValueChange={(value) => setSelected(String(value))}
          orientation="vertical"
          className="grid min-w-0 grid-cols-1 lg:col-span-8 lg:grid-cols-2"
        >
          <div className="border-b p-3 sm:p-4 lg:border-r lg:border-b-0">
            <p id="preview-list-label" className="px-2 pt-1 pb-3 text-sm font-medium">
              Fix first
            </p>
            <Tabs.List
              aria-labelledby="preview-list-label"
              activateOnFocus
              className="flex flex-col gap-1.5"
            >
              {SAMPLE_FINDINGS.map((finding) => (
                <Tabs.Tab
                  key={finding.id}
                  value={finding.id}
                  className={cn(
                    "group flex w-full flex-col items-start gap-2 rounded-xl border border-transparent px-3 py-3 text-left transition-colors",
                    "hover:bg-muted/70 data-active:border-border data-active:bg-card data-active:shadow-card",
                  )}
                >
                  <span className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={finding.severity} />
                    {finding.fixed && <FixedChip />}
                  </span>
                  <span
                    className={cn(
                      "text-sm leading-snug font-medium",
                      finding.fixed && "text-muted-foreground",
                    )}
                  >
                    {finding.plainTitle}
                  </span>
                </Tabs.Tab>
              ))}
            </Tabs.List>
          </div>
          {SAMPLE_FINDINGS.map((finding) => (
            <Tabs.Panel key={finding.id} value={finding.id} className="p-5 sm:p-6">
              <FindingDetail finding={finding} />
            </Tabs.Panel>
          ))}
        </Tabs.Root>
      </div>
    </div>
  );
}
