import { CircleCheck, CircleMinus, ImageOff, OctagonX, type LucideIcon } from "lucide-react";

import { InfoTip } from "@/components/ui/info-tip";
import type { JourneyStepView } from "@/lib/api";
import { resolveScreenshotUrl } from "@/lib/artifacts";
import { TERMS } from "@/lib/glossary";
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
  passed: "bg-verdict-launch-tint text-verdict-launch-fg",
  failed: "bg-sev-critical-tint text-sev-critical-fg",
  skipped: "bg-muted text-muted-foreground",
};

function stepStatus(value: string): JourneyStepStatus {
  if (value === "passed" || value === "failed" || value === "skipped") return value;
  return "skipped";
}

function Heading({ children }: { children?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-0.5">
        <h2 id="journey-heading" className="text-xl">
          Journey through the live app
        </h2>
        <InfoTip term={TERMS.journey.term}>{TERMS.journey.plain}</InfoTip>
      </div>
      {children}
    </div>
  );
}

/**
 * The journey the audit walked through the live app (sign up, log in, add
 * to cart, check out) as a filmstrip of screenshots, each with its outcome
 * and error. Without steps it explains how to get them.
 */
export function JourneySteps({
  steps,
  runId,
  liveUrl = null,
}: {
  steps: JourneyStepView[];
  runId: string;
  /** The run's live URL, used to explain why there are no steps. */
  liveUrl?: string | null;
}) {
  if (steps.length === 0) {
    return (
      <section aria-labelledby="journey-heading" className="flex flex-col gap-4">
        <Heading />
        <div className="flex flex-col items-start gap-5 rounded-2xl border border-dashed border-input/60 bg-card/60 px-5 py-6 sm:flex-row sm:items-center sm:px-6">
          <div aria-hidden="true" className="flex shrink-0 gap-2">
            {[0, 1, 2].map((frame) => (
              <span
                key={frame}
                className={cn(
                  "flex aspect-[4/3] w-14 items-center justify-center rounded-lg border bg-sunken text-muted-foreground",
                  frame === 1 && "-translate-y-1",
                )}
              >
                {frame === 1 ? <ImageOff className="size-4" /> : null}
              </span>
            ))}
          </div>
          <div className="flex max-w-prose flex-col gap-1">
            <h3 className="text-base">No screenshots for this audit</h3>
            <p className="text-sm text-muted-foreground">
              {liveUrl
                ? "The audit checked the live site but did not walk through it. Add a journey login when you rerun, and each screen of sign up, log in and checkout shows up here."
                : "This audit checked the code only. Add the live site and a journey login to an audit, and each screen of sign up, log in and checkout shows up here."}
            </p>
          </div>
        </div>
      </section>
    );
  }

  const failed = steps.filter((step) => stepStatus(step.status) === "failed").length;

  return (
    <section aria-labelledby="journey-heading" className="flex min-w-0 flex-col gap-4">
      <Heading>
        <p className="max-w-prose text-sm text-muted-foreground">
          The audit used the app the way a visitor would and captured each step.{" "}
          {failed > 0
            ? `${failed} of ${steps.length} steps failed.`
            : `All ${steps.length} steps worked.`}
        </p>
      </Heading>
      <ol className="-mx-1 flex snap-x snap-mandatory gap-3 overflow-x-auto px-1 pb-2">
        {steps.map((step, index) => {
          const status = stepStatus(step.status);
          const Icon = STATUS_ICON[status];
          const screenshotUrl = resolveScreenshotUrl(runId, step.screenshot_url);
          return (
            <li
              key={`${step.name}-${index}`}
              className="flex w-60 shrink-0 snap-start flex-col overflow-hidden rounded-2xl border bg-card shadow-xs sm:w-64"
            >
              <div className="relative aspect-[16/10] border-b bg-sunken">
                {screenshotUrl ? (
                  <a
                    href={screenshotUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="block size-full"
                  >
                    {/* Plain img: the screenshot lives on the API origin, and next/image
                        would fetch it server-side instead of from the browser. */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={screenshotUrl}
                      alt={`Screenshot of the ${step.name} step`}
                      loading="lazy"
                      className="size-full object-cover object-top"
                    />
                    <span className="sr-only"> (opens full size in a new tab)</span>
                  </a>
                ) : (
                  <div className="flex size-full flex-col items-center justify-center gap-1.5 text-xs text-muted-foreground">
                    <ImageOff aria-hidden="true" className="size-4" />
                    No screenshot
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-1.5 px-3.5 py-3">
                <div className="flex items-center gap-2">
                  <p className="min-w-0 flex-1 truncate text-sm font-semibold">
                    {index + 1}. {step.name}
                    <span className="sr-only">: {JOURNEY_STEP_STATUS_LABEL[status]}</span>
                  </p>
                  <span
                    aria-hidden="true"
                    className={cn(
                      "inline-flex h-6 shrink-0 items-center gap-1 rounded-sm px-1.5 text-xs font-semibold",
                      STATUS_TONE[status],
                    )}
                  >
                    <Icon className="size-3.5" />
                    {JOURNEY_STEP_STATUS_LABEL[status]}
                  </span>
                </div>
                {step.error ? (
                  <p role="alert" className="text-sm text-sev-critical-fg">
                    {step.error}
                  </p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
