import { Check, Minus } from "lucide-react";

import { cn } from "@/lib/utils";

import { STEPS, type StepDef, type StepStatus } from "./steps";

const STATUS_TEXT: Record<Exclude<StepStatus, "upcoming">, string> = {
  done: "Done",
  skipped: "Skipped",
  current: "Current step",
};

function statusText(step: StepDef, status: StepStatus, isLast: boolean): string {
  if (status !== "upcoming") return STATUS_TEXT[status];
  if (isLast) return "Last step";
  return step.optional ? "Optional" : "Required";
}

function Marker({ status, number }: { status: StepStatus; number: number }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold tabular-nums",
        status === "current" && "bg-primary text-primary-foreground shadow-xs",
        status === "done" && "bg-brand-soft text-brand-fg",
        status === "skipped" && "border border-dashed border-input bg-sunken text-muted-foreground",
        status === "upcoming" && "border border-border bg-card text-muted-foreground",
      )}
    >
      {status === "done" ? (
        <Check className="size-3.5" strokeWidth={2.6} />
      ) : status === "skipped" ? (
        <Minus className="size-3.5" strokeWidth={2.6} />
      ) : (
        number
      )}
    </span>
  );
}

/**
 * The audit steps. Each step shows its state as a shape (number, tick,
 * dash) and as a word, never by colour alone. Steps already reached are
 * buttons, so people can go back to any of them.
 */
export function Stepper({
  current,
  statuses,
  furthest,
  onSelect,
  disabled,
}: {
  current: number;
  statuses: readonly StepStatus[];
  /** Highest step index reached so far; later steps cannot be selected. */
  furthest: number;
  onSelect: (index: number) => void;
  disabled?: boolean;
}) {
  return (
    <ol
      aria-label="Audit steps"
      className="grid grid-cols-4 gap-2 lg:grid-cols-1 lg:gap-0"
    >
      {STEPS.map((step, index) => {
        const status = statuses[index] ?? "upcoming";
        const isLast = index === STEPS.length - 1;
        const isCurrent = index === current;
        const selectable = !isCurrent && index <= furthest && !disabled;
        const word = statusText(step, status, isLast);

        const body = (
          <>
            <Marker status={status} number={index + 1} />
            <span className="flex min-w-0 flex-col items-start text-left">
              <span
                className={cn(
                  "text-xs leading-5 font-medium sm:text-sm",
                  isCurrent || status === "done" ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {step.label}
              </span>
              <span className="sr-only sm:not-sr-only sm:text-xs sm:leading-4 sm:text-muted-foreground">
                {word}
              </span>
            </span>
          </>
        );

        const rowClasses =
          "flex w-full flex-col items-start gap-2 rounded-[10px] py-1.5 sm:flex-row sm:items-center sm:gap-3 lg:py-2.5";

        return (
          <li key={step.id} className="relative min-w-0">
            {isLast ? null : (
              <span
                aria-hidden="true"
                className={cn(
                  "absolute top-[1.3rem] right-1 left-9 h-px sm:hidden lg:block lg:top-[2.6rem] lg:bottom-[-0.6rem] lg:left-[0.85rem] lg:h-auto lg:w-px",
                  index < current ? "bg-brand/40" : "bg-border",
                )}
              />
            )}
            {selectable ? (
              <button
                type="button"
                onClick={() => onSelect(index)}
                className={cn(rowClasses, "group -mx-1.5 px-1.5 transition-colors hover:bg-muted")}
              >
                {body}
                <span className="sr-only">, open this step</span>
              </button>
            ) : (
              <div aria-current={isCurrent ? "step" : undefined} className={rowClasses}>
                {body}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
