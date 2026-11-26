"use client";

import { CircleCheck, OctagonX, TriangleAlert } from "lucide-react";
import * as m from "motion/react-m";

import { InfoTip } from "@/components/ui/info-tip";
import { popIn } from "@/components/ui/motion";
import { ScoreRing } from "@/components/ui/score-ring";
import { SeverityDonut } from "@/components/ui/severity-donut";
import { TERMS, VERDICT_PLAIN } from "@/lib/glossary";
import { formatRiskScore, scoreChangeLabel, VERDICT_LABEL, type Severity, type Verdict } from "@/lib/report";
import { cn } from "@/lib/utils";

const TINT: Record<Verdict, string> = {
  launch: "bg-verdict-launch-tint text-verdict-launch-fg",
  fix_first: "bg-verdict-fix-tint text-verdict-fix-fg",
  do_not_launch: "bg-verdict-block-tint text-verdict-block-fg",
};

/*
  The traffic light. Top to bottom: do not launch, fix first, launch, each
  with its own shape so the lit lamp reads without colour. Decorative: the
  verdict word next to it is the content.
*/
const LAMPS = [
  {
    verdict: "do_not_launch",
    icon: OctagonX,
    lit: "bg-verdict-block shadow-[0_0_16px_1px_var(--verdict-block)]",
    dim: "text-verdict-block",
  },
  {
    verdict: "fix_first",
    icon: TriangleAlert,
    lit: "bg-verdict-fix shadow-[0_0_16px_1px_var(--verdict-fix)]",
    dim: "text-verdict-fix",
  },
  {
    verdict: "launch",
    icon: CircleCheck,
    lit: "bg-verdict-launch shadow-[0_0_16px_1px_var(--verdict-launch)]",
    dim: "text-verdict-launch",
  },
] as const satisfies readonly { verdict: Verdict; icon: unknown; lit: string; dim: string }[];

function TrafficLight({ verdict }: { verdict: Verdict }) {
  return (
    <div
      aria-hidden="true"
      className="flex shrink-0 flex-col gap-1.5 rounded-full bg-foreground p-1.5 shadow-[inset_0_1px_0_rgb(255_255_255/0.12)] dark:bg-black/60 dark:ring-1 dark:ring-white/10"
    >
      {LAMPS.map(({ verdict: lamp, icon: Icon, lit, dim }) =>
        lamp === verdict ? (
          <m.span
            key={lamp}
            variants={popIn}
            className={cn(
              "flex size-9 items-center justify-center rounded-full text-on-solid",
              lit,
            )}
          >
            <Icon className="size-5" strokeWidth={2.25} />
          </m.span>
        ) : (
          <span
            key={lamp}
            className={cn(
              "flex size-9 items-center justify-center rounded-full bg-white/[0.08] opacity-70",
              dim,
            )}
          >
            <Icon className="size-4" strokeWidth={2} />
          </span>
        ),
      )}
    </div>
  );
}

/**
 * The left column of the report: the verdict as a traffic light with one
 * plain sentence, the risk score ring, open problems by severity, and the
 * before and after when this run reran an earlier one.
 */
export function VerdictHero({
  verdict,
  riskScore,
  counts,
  isRerun,
  previousRiskScore,
  scoreChange,
  fixedCount,
  className,
}: {
  verdict: Verdict | null;
  riskScore: number | null;
  counts: Partial<Record<Severity, number>>;
  isRerun: boolean;
  previousRiskScore: number | null;
  scoreChange: number | null;
  fixedCount: number;
  className?: string;
}) {
  const changeLabel = scoreChangeLabel(scoreChange, previousRiskScore, riskScore);

  return (
    <section
      aria-labelledby="verdict-heading"
      className={cn("overflow-hidden rounded-2xl border bg-card shadow-card", className)}
    >
      {verdict ? (
        <m.div
          initial="hidden"
          animate="show"
          className={cn("flex gap-4 px-5 py-5 sm:px-6", TINT[verdict])}
        >
          <TrafficLight verdict={verdict} />
          <div className="flex min-w-0 flex-col gap-1.5 pt-0.5">
            <div className="flex items-center gap-0.5 text-sm font-medium opacity-90">
              <h2 id="verdict-heading">Verdict</h2>
              <InfoTip term={TERMS.verdict.term} className="text-current hover:bg-black/5 dark:hover:bg-white/10">
                {TERMS.verdict.plain}
              </InfoTip>
            </div>
            <m.p
              variants={popIn}
              data-verdict={verdict}
              className="font-heading text-4xl leading-none font-semibold tracking-[-0.03em] text-balance"
            >
              {VERDICT_LABEL[verdict]}
            </m.p>
            <p className="mt-1.5 text-base leading-snug text-pretty text-foreground">
              {VERDICT_PLAIN[verdict]}
            </p>
          </div>
        </m.div>
      ) : (
        <div className="flex flex-col gap-1.5 bg-sunken px-5 py-5 sm:px-6">
          <h2 id="verdict-heading" className="text-sm font-medium text-muted-foreground">
            Verdict
          </h2>
          <p className="text-base">No verdict yet. The audit has not finished.</p>
        </div>
      )}

      <div className="flex items-center gap-5 border-b px-5 py-5 sm:px-6">
        {riskScore !== null ? (
          <ScoreRing score={riskScore} verdict={verdict} size={128} className="shrink-0" />
        ) : (
          <div
            aria-hidden="true"
            className="size-32 shrink-0 rounded-full border-[10px] border-muted"
          />
        )}
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex items-center gap-0.5">
            <h3 className="text-base">Risk score</h3>
            <InfoTip term={TERMS.riskScore.term}>{TERMS.riskScore.plain}</InfoTip>
          </div>
          <p className="text-sm text-muted-foreground">
            {riskScore !== null
              ? "0 is safest and 10 is the most at risk. It drops as you fix problems."
              : "Not scored yet."}
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 px-5 py-5 sm:px-6">
        <h3 className="text-base">Open problems by severity</h3>
        <SeverityDonut counts={counts} />
      </div>

      {isRerun ? (
        <div className="flex flex-col gap-3 border-t bg-sunken/60 px-5 py-5 sm:px-6">
          <h3 className="text-base">Since the last run</h3>
          <dl className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-0.5">
              <dt className="text-xs text-muted-foreground">Before</dt>
              <dd className="font-sans text-xl font-semibold tabular-nums">
                {previousRiskScore !== null ? formatRiskScore(previousRiskScore) : "None"}
              </dd>
            </div>
            <div className="flex flex-col gap-0.5">
              <dt className="text-xs text-muted-foreground">Now</dt>
              <dd className="font-sans text-xl font-semibold tabular-nums">
                {riskScore !== null ? formatRiskScore(riskScore) : "None"}
              </dd>
            </div>
            <div className="flex flex-col gap-0.5">
              <dt className="text-xs text-muted-foreground">Problems fixed</dt>
              <dd className="font-sans text-xl font-semibold tabular-nums">{fixedCount}</dd>
            </div>
          </dl>
          {changeLabel ? (
            <p className="text-sm text-muted-foreground">{changeLabel}</p>
          ) : null}
          {fixedCount === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nothing from the last run is fixed yet.
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
