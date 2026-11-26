"use client";

import { KeyRound, RotateCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { InfoTip } from "@/components/ui/info-tip";
import { TERMS } from "@/lib/glossary";
import { useRerunRun } from "@/hooks/use-run";
import { isApiError, type RerunRequest } from "@/lib/api";
import { cn } from "@/lib/utils";

const inputClasses =
  "h-10 w-full rounded-[10px] border border-input bg-card px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30";

/**
 * Re-runs the audit after fixes. Journey credentials and the domain token
 * are never stored by the API, so the button offers fields for fresh ones;
 * without them the rerun still re-scans the code and the live URL.
 * `children` (other report actions) sit at the end of the button row.
 */
export function RerunButton({
  runId,
  hasJourney,
  className,
  children,
}: {
  runId: string;
  /** True when the original run had journey steps (so credentials matter). */
  hasJourney: boolean;
  className?: string;
  children?: ReactNode;
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
      <div className="flex items-center gap-2">
        <Button type="button" onClick={() => void start()} disabled={starting}>
          <RotateCcw aria-hidden="true" className={cn("size-4", starting && "animate-spin [animation-direction:reverse]")} />
          {starting ? "Starting rerun…" : "Rerun audit"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => setShowForm((value) => !value)}
          aria-expanded={showForm}
          aria-controls="rerun-journey-form"
          className="text-muted-foreground"
        >
          <KeyRound aria-hidden="true" className="size-4" />
          <span className="max-sm:sr-only">
            {showForm ? "Hide journey login" : "Add journey login"}
          </span>
        </Button>
        {children ? <div className="ml-auto flex items-center gap-2">{children}</div> : null}
      </div>

      {showForm ? (
        <div
          id="rerun-journey-form"
          className="flex max-h-[55vh] animate-in flex-col gap-3 overflow-y-auto rounded-xl border bg-card p-4 duration-200 fade-in-0 lg:max-h-none"
        >
          <div className="flex items-start gap-1">
            <p className="text-sm text-muted-foreground">
              {hasJourney
                ? "The last run walked the journey with a test login. That login was not stored, so enter it again to repeat the journey."
                : "If the app needs a login for the journey (sign up, log in, cart, checkout), enter a test account. It is used once and never stored."}
            </p>
            <InfoTip term={TERMS.journey.term}>{TERMS.journey.plain}</InfoTip>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
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
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-0.5">
              <label htmlFor="rerun-domain-token" className="text-sm font-medium">
                Domain verification token{" "}
                <span className="font-normal text-muted-foreground">(optional)</span>
              </label>
              <InfoTip term={TERMS.domainToken.term}>{TERMS.domainToken.plain}</InfoTip>
            </div>
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
