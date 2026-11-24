import { CircleCheck, CircleMinus, OctagonX, type LucideIcon } from "lucide-react";

import type { JourneyStepView } from "@/lib/api";
import { resolveScreenshotUrl } from "@/lib/artifacts";
import {
  JOURNEY_STEP_STATUS_LABEL,
  type JourneyStepStatus,
} from "@/lib/report";
import { cn } from "@/lib/utils";

const STATUS_ICON: Record<JourneyStepStatus, LucideIcon> = {
  passed: CircleCheck,
  failed: OctagonX,
  skipped: CircleMinus,
};

const STATUS_TONE: Record<JourneyStepStatus, string> = {
  passed: "text-verdict-launch",
  failed: "text-sev-critical",
  skipped: "text-muted-foreground",
};

function stepStatus(value: string): JourneyStepStatus {
  if (value === "passed" || value === "failed" || value === "skipped") return value;
  return "skipped";
}

/**
 * The journey the audit walked through the live app (sign up, log in, add
 * to cart, check out), each step with its outcome, error and screenshot,
 * drawn as a connected timeline: a node per step on one rail, pass or fail
 * shown by the node icon. Renders nothing when the run has no journey steps.
 */
export function JourneySteps({
  steps,
  runId,
}: {
  steps: JourneyStepView[];
  runId: string;
}) {
  if (steps.length === 0) return null;

  return (
    <section aria-labelledby="journey-heading" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 id="journey-heading" className="text-xl font-semibold tracking-tight">
          Journey through the live app
        </h2>
        <p className="max-w-prose text-sm text-muted-foreground">
          The audit walked the app as a visitor would, and captured each step.
        </p>
      </div>
      <ol className="flex flex-col">
        {steps.map((step, index) => {
          const status = stepStatus(step.status);
          const Icon = STATUS_ICON[status];
          const screenshotUrl = resolveScreenshotUrl(runId, step.screenshot_url);
          const isLast = index === steps.length - 1;
          return (
            <li key={`${step.name}-${index}`} className="flex gap-4 pb-4 last:pb-0">
              {/* Timeline rail: node with the outcome icon, connector down
                  to the next step. Decorative; the step text names the outcome. */}
              <div aria-hidden="true" className="flex flex-col items-center">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full border bg-card">
                  <Icon className={cn("size-5", STATUS_TONE[status])} />
                </span>
                {isLast ? null : <span className="mt-2 w-0.5 flex-1 bg-border" />}
              </div>
              <div className="flex min-w-0 flex-1 flex-col gap-3 rounded-lg border bg-card px-4 py-3 sm:px-5">
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="font-semibold">
                    {index + 1}. {step.name}
                    <span className="sr-only">
                      : {JOURNEY_STEP_STATUS_LABEL[status]}
                    </span>
                  </p>
                  <p aria-hidden="true" className="text-xs text-muted-foreground">
                    {JOURNEY_STEP_STATUS_LABEL[status]}
                  </p>
                  {step.error ? (
                    <p role="alert" className="text-sm text-sev-critical-fg">
                      {step.error}
                    </p>
                  ) : null}
                </div>
                {screenshotUrl ? (
                  <div className="flex flex-col gap-1">
                    {/* Plain img: the screenshot lives on the API origin, and next/image
                        would fetch it server-side instead of from the browser. */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={screenshotUrl}
                      alt={`Screenshot of the ${step.name} step`}
                      loading="lazy"
                      className="max-w-full rounded-md border"
                    />
                  </div>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
