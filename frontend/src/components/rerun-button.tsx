"use client";

import { RotateCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useRerunRun } from "@/hooks/use-run";
import { isApiError, type RerunRequest } from "@/lib/api";
import { cn } from "@/lib/utils";

const inputClasses =
  "h-9 w-full rounded-md border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

/**
 * Re-runs the audit after fixes. Journey credentials and the domain token
 * are never stored by the API, so the button offers fields for fresh ones;
 * without them the rerun still re-scans the code and the live URL.
 */
export function RerunButton({
  runId,
  hasJourney,
  className,
}: {
  runId: string;
  /** True when the original run had journey steps (so credentials matter). */
  hasJourney: boolean;
  className?: string;
}) {
  const router = useRouter();
  const rerun = useRerunRun();
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [domainToken, setDomainToken] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  async function start() {
    const trimmedEmail = email.trim();
    const hasEmail = trimmedEmail.length > 0;
    const hasPassword = password.length > 0;
    if (hasEmail !== hasPassword) {
      setFormError("Provide both a journey email and password, or neither.");
      return;
    }
    setFormError(null);
    const payload: RerunRequest = {
      journey_email: hasEmail ? trimmedEmail : null,
      journey_password: hasPassword ? password : null,
      domain_token: domainToken.trim() ? domainToken.trim() : null,
    };
    const hasPayload =
      payload.journey_email !== null ||
      payload.journey_password !== null ||
      payload.domain_token !== null;
    // Await the mutation: per-call onSuccess is dropped when the observer
    // loses its listeners (e.g. a remount mid-request), which would
    // silently swallow the navigation.
    setApiError(null);
    setStarting(true);
    try {
      const newRun = await rerun.mutateAsync({
        runId,
        payload: hasPayload ? payload : undefined,
      });
      router.push(`/audits/${newRun.id}`);
    } catch (error) {
      setApiError(
        isApiError(error) ? error.message : "The rerun could not start. Try again.",
      );
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" onClick={() => void start()} disabled={starting}>
          <RotateCcw aria-hidden="true" className="size-4" />
          {starting ? "Starting rerun…" : "Rerun audit"}
        </Button>
        <button
          type="button"
          onClick={() => setShowForm((value) => !value)}
          aria-expanded={showForm}
          className="rounded-md text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          {showForm ? "Hide journey login" : "Add journey login for the rerun"}
        </button>
      </div>

      {showForm ? (
        <div className="flex max-w-md flex-col gap-3 rounded-lg border bg-muted/50 p-4">
          <p className="text-sm text-muted-foreground">
            {hasJourney
              ? "The last run walked the journey with a test login. That login was not stored, so enter it again to repeat the journey."
              : "If the app needs a login for the journey (sign up, log in, cart, checkout), enter a test account. It is used once and never stored."}
          </p>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rerun-journey-email" className="text-sm font-medium">
              Journey test email
            </label>
            <input
              id="rerun-journey-email"
              type="email"
              autoComplete="off"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={inputClasses}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rerun-journey-password" className="text-sm font-medium">
              Journey test password
            </label>
            <input
              id="rerun-journey-password"
              type="password"
              autoComplete="off"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={inputClasses}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rerun-domain-token" className="text-sm font-medium">
              Domain verification token <span className="text-muted-foreground">(optional)</span>
            </label>
            <input
              id="rerun-domain-token"
              type="text"
              autoComplete="off"
              value={domainToken}
              onChange={(event) => setDomainToken(event.target.value)}
              className={inputClasses}
            />
          </div>
        </div>
      ) : null}

      {formError ? (
        <p role="alert" className="text-sm text-sev-critical-fg">
          {formError}
        </p>
      ) : null}
      {apiError ? (
        <p role="alert" className="max-w-prose text-sm text-sev-critical-fg">
          The rerun could not start: {apiError}
        </p>
      ) : null}
    </div>
  );
}
