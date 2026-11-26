"use client";

import { TriangleAlert } from "lucide-react";
import * as m from "motion/react-m";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type MouseEvent,
  type ReactNode,
} from "react";

import { CodeStep, type CodeSource } from "@/components/audit-form/code-step";
import { LiveSiteStep } from "@/components/audit-form/live-site-step";
import { ReviewStep } from "@/components/audit-form/review-step";
import { Stepper } from "@/components/audit-form/stepper";
import {
  firstStepWithError,
  REVIEW_INDEX,
  STEPS,
  type FieldName,
  type StepStatus,
} from "@/components/audit-form/steps";
import { TestLoginStep } from "@/components/audit-form/test-login-step";
import { Button } from "@/components/ui/button";
import { EASE_OUT } from "@/components/ui/motion";
import { useCreateRun } from "@/hooks/use-run";
import { isApiError, type CreateRunInput } from "@/lib/api";
import {
  EMPTY_AUDIT_FORM,
  validateAuditForm,
  type AuditFormErrors,
  type AuditFormValues,
} from "@/lib/audit-form";

/** The input that shows each field's error, for moving focus to it. */
const FIELD_INPUT_ID: Record<FieldName, string> = {
  projectName: "project-name",
  repoUrl: "repo-url",
  zipFile: "zip-file",
  liveUrl: "live-url",
  domainToken: "domain-token",
  journeyEmail: "journey-email",
  journeyPassword: "journey-password",
};

/** Keeps the field from losing focus on press, so a blur error cannot shift the button away. */
function keepFocus(event: MouseEvent) {
  event.preventDefault();
}

function isEmpty(value: AuditFormValues[FieldName]): boolean {
  return value === null || (typeof value === "string" && value.trim() === "");
}

/** One step: its heading (focused when the step opens) and help line. */
function StepPanel({
  index,
  focusOnMount,
  children,
}: {
  index: number;
  focusOnMount: boolean;
  children: ReactNode;
}) {
  const step = STEPS[index]!;
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (focusOnMount) headingRef.current?.focus();
  }, [focusOnMount]);

  return (
    <section aria-labelledby={`step-${step.id}-heading`} className="flex flex-col gap-7">
      <header className="flex flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <h2
            ref={headingRef}
            id={`step-${step.id}-heading`}
            tabIndex={-1}
            className="scroll-mt-24 rounded-[6px] text-2xl text-foreground"
          >
            <span className="sr-only">
              Step {index + 1} of {STEPS.length}:{" "}
            </span>
            {step.title}
          </h2>
          {step.optional ? (
            <span className="rounded-[6px] border border-border bg-sunken px-2 py-0.5 text-xs font-medium text-muted-foreground">
              Optional
            </span>
          ) : null}
        </div>
        <p className="text-base text-muted-foreground">{step.help}</p>
      </header>
      {children}
    </section>
  );
}

/**
 * The new-audit form as four steps: code, live site, test login, review.
 * Only the code is required. Errors show when a field loses focus or on
 * Next, never while typing. Submitting from Review starts the run and moves
 * to the run page. No account is needed; the run is reachable from its link.
 */
export function AuditForm() {
  const router = useRouter();
  const createRun = useCreateRun();
  const [values, setValues] = useState<AuditFormValues>(EMPTY_AUDIT_FORM);
  const [errors, setErrors] = useState<AuditFormErrors>({});
  const [touched, setTouched] = useState<ReadonlySet<FieldName>>(() => new Set());
  const [step, setStep] = useState(0);
  const [furthest, setFurthest] = useState(0);
  const [outcomes, setOutcomes] = useState<Partial<Record<number, "done" | "skipped">>>({});
  const [direction, setDirection] = useState<1 | -1>(1);
  const [navigated, setNavigated] = useState(false);
  const [source, setSource] = useState<CodeSource>("repo");
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const current = STEPS[step]!;
  const isReview = step === REVIEW_INDEX;

  /** Shows the current errors for `fields` (and clears fixed ones); returns the invalid fields. */
  function reveal(fields: readonly FieldName[], from: AuditFormValues): FieldName[] {
    const all = validateAuditForm(from);
    setErrors((prev) => {
      const next = { ...prev };
      for (const field of fields) {
        if (all[field]) next[field] = all[field];
        else delete next[field];
      }
      return next;
    });
    return fields.filter((field) => all[field]);
  }

  function setValue<K extends FieldName>(key: K, value: AuditFormValues[K]) {
    const next = { ...values, [key]: value };
    setValues(next);
    if (key === "zipFile") {
      // Picking a file is one action, not typing: check it straight away.
      setTouched((prev) => new Set(prev).add("zipFile"));
      reveal(["zipFile", "repoUrl"], next);
      return;
    }
    // While typing, errors may only go away, never appear.
    const all = validateAuditForm(next);
    setErrors((prev) => {
      const fixed = (Object.keys(prev) as FieldName[]).filter((field) => !all[field]);
      if (fixed.length === 0) return prev;
      const kept = { ...prev };
      for (const field of fixed) delete kept[field];
      return kept;
    });
  }

  function onBlur(key: FieldName) {
    const nextTouched = new Set(touched).add(key);
    setTouched(nextTouched);
    reveal(
      current.fields.filter((field) => nextTouched.has(field)),
      values,
    );
  }

  function forget(fields: readonly FieldName[]) {
    setErrors((prev) => {
      const next = { ...prev };
      for (const field of fields) delete next[field];
      return next;
    });
    setTouched((prev) => {
      const next = new Set(prev);
      for (const field of fields) next.delete(field);
      return next;
    });
  }

  function onSourceChange(next: CodeSource) {
    setSource(next);
    // One input at a time: drop the value of the hidden one.
    setValues((prev) => (next === "zip" ? { ...prev, repoUrl: "" } : { ...prev, zipFile: null }));
    forget(["repoUrl", "zipFile"]);
  }

  function goTo(index: number) {
    setDirection(index >= step ? 1 : -1);
    setStep(index);
    setFurthest((prev) => Math.max(prev, index));
    setNavigated(true);
  }

  function next() {
    const invalid = reveal(current.fields, values);
    setTouched((prev) => new Set([...prev, ...current.fields]));
    if (invalid.length > 0) {
      const first = invalid[0]!;
      const id =
        first === "repoUrl" && source === "zip" ? FIELD_INPUT_ID.zipFile : FIELD_INPUT_ID[first];
      document.getElementById(id)?.focus();
      return;
    }
    const filled = current.fields.some((field) => !isEmpty(values[field]));
    setOutcomes((prev) => ({
      ...prev,
      [step]: current.optional && !filled ? "skipped" : "done",
    }));
    goTo(step + 1);
  }

  function skip() {
    setValues((prev) => {
      const cleared = { ...prev };
      for (const field of current.fields) {
        if (field !== "zipFile") cleared[field] = "";
      }
      return cleared;
    });
    forget(current.fields);
    setOutcomes((prev) => ({ ...prev, [step]: "skipped" }));
    goTo(step + 1);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isReview) {
      next();
      return;
    }
    const nextErrors = validateAuditForm(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      goTo(Math.max(firstStepWithError(nextErrors), 0));
      return;
    }

    const input: CreateRunInput = {
      projectName: values.projectName,
      repoUrl: values.repoUrl || undefined,
      liveUrl: values.liveUrl || undefined,
      zipFile: values.zipFile,
      journeyEmail: values.journeyEmail || undefined,
      journeyPassword: values.journeyPassword || undefined,
      domainToken: values.domainToken || undefined,
    };
    // Await the mutation instead of relying on a per-call onSuccess:
    // TanStack Query drops per-call callbacks when the observer loses its
    // listeners (e.g. the component remounts mid-request), which silently
    // swallowed the navigation. The awaited promise settles either way.
    setApiError(null);
    setSubmitting(true);
    try {
      const run = await createRun.mutateAsync(input);
      router.push(`/audits/${run.id}`);
    } catch (error) {
      setApiError(
        isApiError(error) ? error.message : "The audit could not start. Try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const statuses: StepStatus[] = STEPS.map((_, index) =>
    index === step ? "current" : (outcomes[index] ?? "upcoming"),
  );

  const fieldProps = { values, errors, onChange: setValue, onBlur, disabled: submitting };

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      aria-label="Run an audit"
      className="grid gap-6 lg:grid-cols-[12rem_minmax(0,40rem)] lg:gap-12"
    >
      <div className="lg:sticky lg:top-24 lg:self-start">
        <Stepper
          current={step}
          statuses={statuses}
          furthest={furthest}
          onSelect={goTo}
          disabled={submitting}
        />
      </div>

      <div className="flex min-w-0 flex-col gap-5">
        <div className="overflow-hidden rounded-2xl border border-border bg-card p-5 shadow-card sm:p-8">
          <m.div
            key={step}
            initial={navigated ? { opacity: 0, x: direction * 16 } : false}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.24, ease: EASE_OUT }}
          >
            <StepPanel index={step} focusOnMount={navigated}>
              {current.id === "code" ? (
                <CodeStep {...fieldProps} source={source} onSourceChange={onSourceChange} />
              ) : current.id === "live" ? (
                <LiveSiteStep {...fieldProps} />
              ) : current.id === "login" ? (
                <TestLoginStep {...fieldProps} />
              ) : (
                <ReviewStep values={values} onEdit={goTo} disabled={submitting} />
              )}
            </StepPanel>
          </m.div>
        </div>

        {apiError ? (
          <p
            role="alert"
            className="flex items-start gap-2 rounded-xl border border-sev-critical/30 bg-sev-critical-tint px-4 py-3 text-sm text-sev-critical-fg"
          >
            <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            <span>The audit could not start: {apiError}</span>
          </p>
        ) : null}

        <div className="flex items-center gap-2 max-sm:sticky max-sm:bottom-0 max-sm:z-30 max-sm:-mx-4 max-sm:border-t max-sm:border-border max-sm:bar-solid max-sm:px-4 max-sm:pt-3 max-sm:pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          {step > 0 ? (
            <Button
              type="button"
              variant="outline"
              size="lg"
              onMouseDown={keepFocus}
              onClick={() => goTo(step - 1)}
              disabled={submitting}
            >
              Back
            </Button>
          ) : null}
          <div className="ml-auto flex items-center gap-2">
            {current.optional ? (
              <Button
                type="button"
                variant="ghost"
                size="lg"
                onMouseDown={keepFocus}
                onClick={skip}
                disabled={submitting}
              >
                Skip this step
              </Button>
            ) : null}
            {isReview ? (
              <Button
                key="run"
                type="submit"
                size="lg"
                disabled={submitting}
                onClick={(event) => {
                  // The second click of a double-click on Next lands here.
                  if (event.detail > 1) event.preventDefault();
                }}
              >
                {submitting ? "Starting audit…" : "Run audit"}
              </Button>
            ) : (
              <Button key="next" type="submit" size="lg" onMouseDown={keepFocus}>
                Next
              </Button>
            )}
          </div>
        </div>
      </div>
    </form>
  );
}
