"use client";

import { ChevronDown, ChevronUp, Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DEFAULT_JOURNEY_STEPS,
  MAX_JOURNEY_STEPS,
  type JourneyStepFormValue,
} from "@/lib/audit-form";
import { cn } from "@/lib/utils";

const inputClasses =
  "h-10 w-full rounded-md border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

const labelClasses = "text-sm font-medium";

const ACTION_LABELS: Record<JourneyStepFormValue["action"], string> = {
  goto: "Go to URL",
  fill: "Fill field",
  click: "Click button",
  expect_text: "Expect text",
};

function newStep(): JourneyStepFormValue {
  return {
    id: crypto.randomUUID(),
    action: "goto",
    url: "",
    selector: "",
    value: "",
    text: "",
    name: "",
  };
}

/**
 * The custom journey editor for the new-audit form: add, remove and
 * reorder user-defined steps (go to a URL, fill a field, click a button,
 * expect text). While no steps exist it shows the default journey as
 * read-only info; the run uses the default journey until a step is added.
 */
export function CustomJourneyForm({
  steps,
  onChange,
  disabled,
  error,
}: {
  steps: JourneyStepFormValue[];
  onChange: (steps: JourneyStepFormValue[]) => void;
  disabled?: boolean;
  error?: string;
}) {
  function updateStep(index: number, patch: Partial<JourneyStepFormValue>) {
    onChange(steps.map((step, i) => (i === index ? { ...step, ...patch } : step)));
  }

  function moveStep(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= steps.length) return;
    const current = steps[index];
    const other = steps[target];
    if (!current || !other) return;
    const next = [...steps];
    next[index] = other;
    next[target] = current;
    onChange(next);
  }

  function removeStep(index: number) {
    onChange(steps.filter((_, i) => i !== index));
  }

  function addStep() {
    if (steps.length >= MAX_JOURNEY_STEPS) return;
    onChange([...steps, newStep()]);
  }

  if (steps.length === 0) {
    return (
      <div className="flex flex-col items-start gap-3">
        <p className="text-sm text-muted-foreground">
          Default journey: {DEFAULT_JOURNEY_STEPS.join(", ")}.
        </p>
        <Button
          type="button"
          variant="outline"
          onClick={addStep}
          disabled={disabled}
        >
          <Plus aria-hidden="true" />
          Add a custom step
        </Button>
        {error ? (
          <p role="alert" className="text-sm text-sev-critical-fg">
            {error}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-prose text-sm text-muted-foreground">
        These steps run instead of the default journey. Every go-to URL must
        stay on your live site.
      </p>
      <ol className="flex flex-col gap-4">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const fieldId = (field: string) => `journey-${step.id}-${field}`;
          return (
            <li
              key={step.id}
              className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">Step {stepNumber}</span>
                <span className="flex items-center gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Move step ${stepNumber} up`}
                    onClick={() => moveStep(index, -1)}
                    disabled={disabled || index === 0}
                  >
                    <ChevronUp aria-hidden="true" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Move step ${stepNumber} down`}
                    onClick={() => moveStep(index, 1)}
                    disabled={disabled || index === steps.length - 1}
                  >
                    <ChevronDown aria-hidden="true" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Remove step ${stepNumber}`}
                    onClick={() => removeStep(index)}
                    disabled={disabled}
                  >
                    <X aria-hidden="true" />
                  </Button>
                </span>
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor={fieldId("action")} className={labelClasses}>
                  Action
                </label>
                <select
                  id={fieldId("action")}
                  value={step.action}
                  onChange={(event) =>
                    updateStep(index, {
                      action: event.target.value as JourneyStepFormValue["action"],
                    })
                  }
                  disabled={disabled}
                  className={inputClasses}
                >
                  {(
                    Object.keys(ACTION_LABELS) as JourneyStepFormValue["action"][]
                  ).map((action) => (
                    <option key={action} value={action}>
                      {ACTION_LABELS[action]}
                    </option>
                  ))}
                </select>
              </div>
              {step.action === "goto" ? (
                <div className="flex flex-col gap-1.5">
                  <label htmlFor={fieldId("url")} className={labelClasses}>
                    URL
                  </label>
                  <input
                    id={fieldId("url")}
                    type="text"
                    autoComplete="off"
                    value={step.url}
                    onChange={(event) => updateStep(index, { url: event.target.value })}
                    disabled={disabled}
                    placeholder="/reset-password"
                    className={cn(inputClasses, "font-mono text-[0.85rem]")}
                  />
                </div>
              ) : null}
              {step.action === "fill" || step.action === "click" ? (
                <div className="flex flex-col gap-1.5">
                  <label htmlFor={fieldId("selector")} className={labelClasses}>
                    Selector
                  </label>
                  <input
                    id={fieldId("selector")}
                    type="text"
                    autoComplete="off"
                    value={step.selector}
                    onChange={(event) =>
                      updateStep(index, { selector: event.target.value })
                    }
                    disabled={disabled}
                    placeholder={
                      step.action === "fill" ? "#email" : 'button[type="submit"]'
                    }
                    className={cn(inputClasses, "font-mono text-[0.85rem]")}
                  />
                </div>
              ) : null}
              {step.action === "fill" ? (
                <div className="flex flex-col gap-1.5">
                  <label htmlFor={fieldId("value")} className={labelClasses}>
                    Value
                  </label>
                  <input
                    id={fieldId("value")}
                    type="text"
                    autoComplete="off"
                    value={step.value}
                    onChange={(event) => updateStep(index, { value: event.target.value })}
                    disabled={disabled}
                    placeholder="user@example.com"
                    className={inputClasses}
                  />
                </div>
              ) : null}
              {step.action === "expect_text" ? (
                <div className="flex flex-col gap-1.5">
                  <label htmlFor={fieldId("text")} className={labelClasses}>
                    Expected text
                  </label>
                  <input
                    id={fieldId("text")}
                    type="text"
                    autoComplete="off"
                    value={step.text}
                    onChange={(event) => updateStep(index, { text: event.target.value })}
                    disabled={disabled}
                    placeholder="Check your email"
                    className={inputClasses}
                  />
                </div>
              ) : null}
              <div className="flex flex-col gap-1.5">
                <label htmlFor={fieldId("name")} className={labelClasses}>
                  Step name{" "}
                  <span className="font-normal text-muted-foreground">(optional)</span>
                </label>
                <input
                  id={fieldId("name")}
                  type="text"
                  autoComplete="off"
                  maxLength={100}
                  value={step.name}
                  onChange={(event) => updateStep(index, { name: event.target.value })}
                  disabled={disabled}
                  placeholder="Open the reset page"
                  className={inputClasses}
                />
              </div>
            </li>
          );
        })}
      </ol>
      <div className="flex flex-col items-start gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={addStep}
          disabled={disabled || steps.length >= MAX_JOURNEY_STEPS}
        >
          <Plus aria-hidden="true" />
          Add step
        </Button>
        {steps.length >= MAX_JOURNEY_STEPS ? (
          <p className="text-sm text-muted-foreground">
            A custom journey has at most {MAX_JOURNEY_STEPS} steps.
          </p>
        ) : null}
      </div>
      {error ? (
        <p role="alert" className="text-sm text-sev-critical-fg">
          {error}
        </p>
      ) : null}
    </div>
  );
}
