"use client";

import { Check, CircleDashed, LoaderCircle, Minus, X, type LucideIcon } from "lucide-react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import { popIn } from "@/components/ui/motion";
import { cn } from "@/lib/utils";

import { STAGE_STATE_LABEL, type StageState, type StageView } from "./run-stages";

const NODE: Record<StageState, { icon: LucideIcon; node: string; text: string; spin?: boolean }> = {
  done: {
    icon: Check,
    node: "bg-foreground text-background",
    text: "text-muted-foreground",
  },
  running: {
    icon: LoaderCircle,
    node: "bg-brand-soft text-brand ring-2 ring-brand",
    text: "text-brand-fg font-semibold",
    spin: true,
  },
  failed: {
    icon: X,
    node: "bg-sev-critical text-on-solid",
    text: "text-sev-critical-fg font-semibold",
  },
  pending: {
    icon: CircleDashed,
    node: "bg-card text-muted-foreground ring-1 ring-input",
    text: "text-muted-foreground",
  },
  not_run: {
    icon: CircleDashed,
    node: "bg-sunken text-muted-foreground ring-1 ring-border",
    text: "text-muted-foreground",
  },
  skipped: {
    icon: Minus,
    node: "bg-sunken text-muted-foreground ring-1 ring-border",
    text: "text-muted-foreground",
  },
};

function StageNode({ state }: { state: StageState }) {
  const { icon: Icon, node, spin } = NODE[state];
  return (
    <span aria-hidden="true" className="relative z-10 flex size-7 shrink-0 items-center justify-center">
      {/* No entrance on first paint; a stage that changes state pops in. */}
      <AnimatePresence initial={false} mode="wait">
        <m.span
          key={state}
          variants={popIn}
          initial="hidden"
          animate="show"
          exit={{ opacity: 0, transition: { duration: 0.1 } }}
          className={cn("flex size-7 items-center justify-center rounded-full", node)}
        >
          <Icon
            className={cn("size-4", spin && "motion-safe:animate-spin")}
            strokeWidth={state === "done" || state === "failed" ? 2.75 : 2}
          />
        </m.span>
      </AnimatePresence>
    </span>
  );
}

/**
 * The audit as a vertical pipeline. Each stage pairs its state word with an
 * icon, so the state never depends on colour. The rail turns solid ink up
 * to the furthest stage that has started.
 */
export function RunPipeline({ stages, className }: { stages: StageView[]; className?: string }) {
  // The rail is solid up to the furthest stage that has started.
  let reached = -1;
  stages.forEach((stage, index) => {
    if (stage.state === "done" || stage.state === "running" || stage.state === "failed") reached = index;
  });

  return (
    <ol aria-label="Audit stages" className={cn("flex flex-col", className)}>
      {stages.map((stage, index) => {
        const { text } = NODE[stage.state];
        const last = index === stages.length - 1;
        const solidRail = index < reached;
        const detail =
          stage.state === "skipped" ? "Skipped because the audit has no live URL." : stage.detail;
        return (
          <li
            key={stage.id}
            data-stage={stage.id}
            data-state={stage.state}
            className={cn("relative flex gap-4", last ? "" : "pb-6")}
          >
            {last ? null : (
              <span
                aria-hidden="true"
                className={cn(
                  "absolute top-7 bottom-0 left-[13px] w-0.5",
                  solidRail ? "bg-foreground" : "bg-border",
                )}
              />
            )}
            <StageNode state={stage.state} />
            <div className="flex min-w-0 flex-1 flex-col gap-0.5 pt-0.5">
              <div className="flex items-baseline justify-between gap-3">
                <p
                  className={cn(
                    "font-medium",
                    stage.state === "pending" || stage.state === "not_run" || stage.state === "skipped"
                      ? "text-muted-foreground"
                      : "text-foreground",
                  )}
                >
                  {stage.label}
                </p>
                <span className={cn("shrink-0 text-sm", text)}>{STAGE_STATE_LABEL[stage.state]}</span>
              </div>
              <p className="max-w-prose text-sm text-muted-foreground">{detail}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
