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
 * to cart, check out), each step with its outcome, error and screenshot.
 * Renders nothing when the run has no journey steps.
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
          The audit signed up, logged in, added to the cart and checked out as
          a visitor would, and captured each step.
        </p>
      </div>
      <ol className="flex flex-col gap-3">
        {steps.map((step, index) => {
          const status = stepStatus(step.status);
          const Icon = STATUS_ICON[status];
          const screenshotUrl = resolveScreenshotUrl(runId, step.screenshot_url);
          return (
            <li
              key={`${step.name}-${index}`}
              className="flex flex-col gap-3 rounded-lg border bg-card px-4 py-3 sm:px-5"
            >
              <div className="flex items-start gap-3">
                <Icon
                  aria-hidden="true"
                  className={cn("mt-0.5 size-5 shrink-0", STATUS_TONE[status])}
                />
                <div className="flex min-w-0 flex-1 flex-col gap-1">
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
            </li>
          );
        })}
      </ol>
    </section>
  );
}
