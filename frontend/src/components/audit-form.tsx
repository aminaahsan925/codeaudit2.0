"use client";

import { TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ChangeEvent, type FormEvent } from "react";

import { CustomJourneyForm } from "@/components/journey-form";
import { Button } from "@/components/ui/button";
import { useCreateRun } from "@/hooks/use-run";
import { isApiError, type CreateRunInput } from "@/lib/api";
import {
  EMPTY_AUDIT_FORM,
  toJourneyDefinition,
  validateAuditForm,
  type AuditFormErrors,
  type AuditFormValues,
} from "@/lib/audit-form";
import { cn } from "@/lib/utils";

const inputClasses =
  "h-10 w-full rounded-md border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

const labelClasses = "text-sm font-medium";

function FieldError({ message, id }: { message?: string; id: string }) {
  if (!message) return null;
  return (
    <p id={id} role="alert" className="text-sm text-sev-critical-fg">
      {message}
    </p>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * The new-audit form: project name, code (GitHub repo or zip), live URL
 * and journey login. Submitting starts the run and moves to the run page.
 * No account is needed; the run is reachable from its link. Domain
 * verification uses a server-issued token (see the live section below),
 * never a token typed here.
 */
export function AuditForm() {
  const router = useRouter();
  const createRun = useCreateRun();
  const [values, setValues] = useState<AuditFormValues>(EMPTY_AUDIT_FORM);
  const [errors, setErrors] = useState<AuditFormErrors>({});
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  function setValue<K extends keyof AuditFormValues>(
    key: K,
    value: AuditFormValues[K],
  ) {
    const next = { ...values, [key]: value };
    setValues(next);
    if (attempted) setErrors(validateAuditForm(next));
  }

  function onZipChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setValue("zipFile", file);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validateAuditForm(values);
    setErrors(nextErrors);
    setAttempted(true);
    if (Object.keys(nextErrors).length > 0) return;

    const input: CreateRunInput = {
      projectName: values.projectName,
      repoUrl: values.repoUrl || undefined,
      liveUrl: values.liveUrl || undefined,
      zipFile: values.zipFile,
      journeyEmail: values.journeyEmail || undefined,
      journeyPassword: values.journeyPassword || undefined,
      journeyDefinition: toJourneyDefinition(values.journeySteps),
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

  return (
    <form onSubmit={onSubmit} noValidate className="flex max-w-prose flex-col gap-8">
      <section aria-labelledby="project-heading" className="flex flex-col gap-4">
        <h2 id="project-heading" className="text-xl font-semibold tracking-tight">
          Your project
        </h2>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="project-name" className={labelClasses}>
            Project name
          </label>
          <input
            id="project-name"
            type="text"
            autoComplete="off"
            maxLength={200}
            value={values.projectName}
            onChange={(event) => setValue("projectName", event.target.value)}
            aria-invalid={Boolean(errors.projectName)}
            aria-describedby={errors.projectName ? "project-name-error" : undefined}
            disabled={submitting}
            placeholder="pocket-notes"
            className={inputClasses}
          />
          <FieldError message={errors.projectName} id="project-name-error" />
        </div>
      </section>

      <section aria-labelledby="code-heading" className="flex flex-col gap-4">
        <h2 id="code-heading" className="text-xl font-semibold tracking-tight">
          Your code
        </h2>
        <p className="-mt-2 max-w-prose text-sm text-muted-foreground">
          Add one of these. The code is read, never installed or run.
        </p>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="repo-url" className={labelClasses}>
            GitHub repo URL
          </label>
          <input
            id="repo-url"
            type="url"
            autoComplete="off"
            value={values.repoUrl}
            onChange={(event) => setValue("repoUrl", event.target.value)}
            aria-invalid={Boolean(errors.repoUrl)}
            aria-describedby={errors.repoUrl ? "repo-url-error" : undefined}
            disabled={submitting}
            placeholder="https://github.com/owner/repo"
            className={cn(inputClasses, "font-mono text-[0.85rem]")}
          />
          <FieldError message={errors.repoUrl} id="repo-url-error" />
        </div>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span aria-hidden="true" className="h-px flex-1 bg-border" />
          or
          <span aria-hidden="true" className="h-px flex-1 bg-border" />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="zip-file" className={labelClasses}>
            Zip upload <span className="text-muted-foreground">(max 10 MB)</span>
          </label>
          <input
            id="zip-file"
            type="file"
            accept=".zip,application/zip"
            onChange={onZipChange}
            aria-invalid={Boolean(errors.zipFile)}
            aria-describedby={errors.zipFile ? "zip-file-error" : "zip-file-help"}
            disabled={submitting}
            className="rounded-md border border-input bg-card px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-1.5 file:text-sm file:font-medium"
          />
          <p id="zip-file-help" className="text-xs text-muted-foreground">
            {values.zipFile
              ? `Selected: ${values.zipFile.name} (${formatFileSize(values.zipFile.size)})`
              : "A zip of the project source."}
          </p>
          <FieldError message={errors.zipFile} id="zip-file-error" />
        </div>
      </section>

      <section aria-labelledby="live-heading" className="flex flex-col gap-4">
        <h2 id="live-heading" className="text-xl font-semibold tracking-tight">
          Your live app <span className="text-base font-normal text-muted-foreground">(optional)</span>
        </h2>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="live-url" className={labelClasses}>
            Live URL
          </label>
          <input
            id="live-url"
            type="url"
            autoComplete="off"
            value={values.liveUrl}
            onChange={(event) => setValue("liveUrl", event.target.value)}
            aria-invalid={Boolean(errors.liveUrl)}
            aria-describedby={errors.liveUrl ? "live-url-error" : "live-url-help"}
            disabled={submitting}
            placeholder="https://app.example.com"
            className={cn(inputClasses, "font-mono text-[0.85rem]")}
          />
          <p id="live-url-help" className="text-xs text-muted-foreground">
            The running app. Live checks only start after you verify you own the
            domain.
          </p>
          <FieldError message={errors.liveUrl} id="live-url-error" />
        </div>
        <p className="-mt-1 text-xs text-muted-foreground">
          To verify a domain, request a token (POST /api/verification/token),
          serve it at the well-known URL in the response, then confirm it
          (POST /api/verification/check). Without it, live checks are skipped.
        </p>
      </section>

      <section aria-labelledby="journey-heading" className="flex flex-col gap-4">
        <h2 id="journey-heading" className="text-xl font-semibold tracking-tight">
          Journey login <span className="text-base font-normal text-muted-foreground">(optional)</span>
        </h2>
        <p className="-mt-2 max-w-prose text-sm text-muted-foreground">
          A test account the audit uses to walk the journey: sign up, log in,
          add to cart, check out. It is used once for this run and never stored.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="journey-email" className={labelClasses}>
              Journey test email
            </label>
            <input
              id="journey-email"
              type="email"
              autoComplete="off"
              value={values.journeyEmail}
              onChange={(event) => setValue("journeyEmail", event.target.value)}
              aria-invalid={Boolean(errors.journeyEmail)}
              aria-describedby={
                errors.journeyEmail ? "journey-email-error" : undefined
              }
              disabled={submitting}
              placeholder="tester@example.com"
              className={inputClasses}
            />
            <FieldError message={errors.journeyEmail} id="journey-email-error" />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="journey-password" className={labelClasses}>
              Journey test password
            </label>
            <input
              id="journey-password"
              type="password"
              autoComplete="off"
              value={values.journeyPassword}
              onChange={(event) => setValue("journeyPassword", event.target.value)}
              aria-invalid={Boolean(errors.journeyPassword)}
              aria-describedby={
                errors.journeyPassword ? "journey-password-error" : undefined
              }
              disabled={submitting}
              className={inputClasses}
            />
            <FieldError message={errors.journeyPassword} id="journey-password-error" />
          </div>
        </div>
      </section>

      <section aria-labelledby="custom-journey-heading" className="flex flex-col gap-4">
        <h2 id="custom-journey-heading" className="text-xl font-semibold tracking-tight">
          Custom journey <span className="text-base font-normal text-muted-foreground">(optional)</span>
        </h2>
        <p className="-mt-2 max-w-prose text-sm text-muted-foreground">
          Walk a flow of your own, such as a password reset: go to a page,
          fill a field, click a button, expect text. Leave it empty to run
          the default journey.
        </p>
        <CustomJourneyForm
          steps={values.journeySteps}
          onChange={(steps) => setValue("journeySteps", steps)}
          disabled={submitting}
          error={errors.journeySteps}
        />
      </section>

      {apiError ? (
        <p role="alert" className="flex items-start gap-2 text-sm text-sev-critical-fg">
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span>The audit could not start: {apiError}</span>
        </p>
      ) : null}

      <div className="flex flex-col gap-3 border-t pt-6">
        <div>
          <Button type="submit" size="lg" disabled={submitting}>
            {submitting ? "Starting audit…" : "Run audit"}
          </Button>
        </div>
        <p className="max-w-prose text-sm text-muted-foreground">
          No account needed. The run is reachable from its link, so keep the
          link safe.
        </p>
      </div>
    </form>
  );
}
