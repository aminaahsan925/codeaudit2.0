"use client";

import { useId } from "react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useHealth } from "@/hooks/use-health";
import { cn } from "@/lib/utils";

type HealthState = "checking" | "online" | "offline";

const label: Record<HealthState, string> = {
  checking: "Checking API",
  online: "API online",
  offline: "API offline",
};

/* Calm while healthy; only the offline state takes a tint. */
const tone: Record<HealthState, string> = {
  checking: "border-border bg-card text-muted-foreground",
  online: "border-border bg-card text-foreground hover:border-input",
  offline: "border-verdict-block/45 bg-verdict-block-tint text-verdict-block-fg",
};

/** Shape differs per state so it does not rely on colour. */
function StatusMark({ state }: { state: HealthState }) {
  if (state === "checking") {
    return (
      <span
        aria-hidden="true"
        className="size-2 shrink-0 animate-pulse rounded-full border-2 border-current"
      />
    );
  }
  if (state === "online") {
    return (
      <span
        aria-hidden="true"
        className="size-2 shrink-0 rounded-full bg-verdict-launch shadow-[0_0_0_3px_color-mix(in_oklab,var(--verdict-launch)_18%,transparent)]"
      />
    );
  }
  return (
    <svg
      viewBox="0 0 8 8"
      aria-hidden="true"
      className="size-2 shrink-0 stroke-verdict-block"
      strokeWidth="2"
    >
      <path d="M1 1l6 6M7 1 1 7" />
    </svg>
  );
}

/**
 * API status chip. `compact` shows only the status mark (the sidebar rail);
 * the accessible name and description stay the same.
 */
export function HealthBadge({
  className,
  compact = false,
  side = "bottom",
}: {
  className?: string;
  compact?: boolean;
  side?: "top" | "bottom" | "right";
}) {
  const detailId = useId();
  const { status, data, error, refetch, isFetching } = useHealth();
  const state: HealthState =
    status === "pending" ? "checking" : status === "error" ? "offline" : "online";

  const detail =
    state === "online"
      ? `Version ${data?.version ?? "unknown"}. Checked every 30 seconds.`
      : state === "offline"
        ? (error?.message ?? "The API is not responding.")
        : "Contacting the LaunchAudit API.";

  return (
    <>
      <Tooltip>
        <TooltipTrigger
          render={
            <button
              type="button"
              onClick={() => {
                if (!isFetching) void refetch();
              }}
              aria-label={label[state]}
              aria-describedby={detailId}
              className={cn(
                "inline-flex h-8 items-center gap-2 rounded-[8px] border text-xs font-medium whitespace-nowrap shadow-xs transition-colors",
                compact ? "w-8 justify-center px-0" : "px-2.5",
                tone[state],
                className,
              )}
            />
          }
        >
          <StatusMark state={state} />
          {compact ? null : (
            <span>{label[state]}</span>
          )}
        </TooltipTrigger>
        <TooltipContent side={side} sideOffset={8} className="max-w-64 text-left">
          {detail} {state !== "checking" && "Select to check now."}
        </TooltipContent>
      </Tooltip>
      <span id={detailId} className="sr-only">
        {detail}
      </span>
      <span role="status" aria-live="polite" className="sr-only">
        {`LaunchAudit ${label[state]}`}
      </span>
    </>
  );
}
