import { KeyRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import { InfoTip } from "@/components/ui/info-tip";
import { TERMS } from "@/lib/glossary";

import { CopySnippet } from "./copy-snippet";
import { describedBy, FieldError, FieldHint, FieldLabel, monoInputClasses } from "./field";
import type { StepFieldProps } from "./steps";

/** Matches the backend (services/live/verify.py). */
const VERIFICATION_PATH = "/.well-known/launchaudit-verification.txt";
const META_NAME = "launchaudit-verification";

/** A random token the founder can publish; any string works. */
function makeToken(): string {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return `la-${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

function fileAddress(liveUrl: string): string {
  try {
    return new URL(VERIFICATION_PATH, liveUrl).toString();
  } catch {
    return VERIFICATION_PATH;
  }
}

export function LiveSiteStep({ values, errors, onChange, onBlur, disabled }: StepFieldProps) {
  const token = values.domainToken.trim();
  const shownToken = token || "your-token";

  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-col gap-1.5">
        <FieldLabel htmlFor="live-url">Live site URL</FieldLabel>
        <input
          id="live-url"
          type="url"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          value={values.liveUrl}
          onChange={(event) => onChange("liveUrl", event.target.value)}
          onBlur={() => onBlur("liveUrl")}
          aria-invalid={Boolean(errors.liveUrl)}
          aria-describedby={describedBy("live-url-help", errors.liveUrl && "live-url-error")}
          disabled={disabled}
          placeholder="https://app.example.com"
          className={monoInputClasses}
        />
        <FieldHint id="live-url-help">The address people open to use your app.</FieldHint>
        <FieldError id="live-url-error" message={errors.liveUrl} />
      </div>

      <section
        aria-labelledby="verify-heading"
        className="flex flex-col gap-5 rounded-2xl border border-border bg-sunken/60 p-4 sm:p-5"
      >
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1">
            <h3 id="verify-heading" className="text-base">
              Prove the site is yours
            </h3>
            <InfoTip term={TERMS.domainToken.term}>{TERMS.domainToken.plain}</InfoTip>
          </div>
          <p className="text-sm text-muted-foreground">
            Publish a token on your site, then enter it here. Without it, we skip the live
            checks and only read your code.
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <FieldLabel htmlFor="domain-token">Domain verification token</FieldLabel>
          <div className="flex gap-2">
            <input
              id="domain-token"
              type="text"
              autoComplete="off"
              spellCheck={false}
              value={values.domainToken}
              onChange={(event) => onChange("domainToken", event.target.value)}
              onBlur={() => onBlur("domainToken")}
              aria-invalid={Boolean(errors.domainToken)}
              aria-describedby={describedBy(
                "domain-token-help",
                errors.domainToken && "domain-token-error",
              )}
              disabled={disabled}
              className={monoInputClasses}
            />
            <Button
              type="button"
              variant="outline"
              onClick={() => onChange("domainToken", makeToken())}
              disabled={disabled}
              className="h-10 shrink-0"
            >
              <KeyRound aria-hidden="true" className="size-4" />
              Create one
            </Button>
          </div>
          <FieldHint id="domain-token-help">Any text works. Create one if you have none.</FieldHint>
          <FieldError id="domain-token-error" message={errors.domainToken} />
        </div>

        <div className="flex flex-col gap-4">
          <p className="text-sm text-foreground">Then publish the token in one of two ways.</p>
          <CopySnippet
            id="verify-meta"
            label="Add this tag inside the <head> of your home page"
            value={`<meta name="${META_NAME}" content="${shownToken}">`}
            copyLabel="Copy tag"
            disabled={disabled || !token}
          />
          <CopySnippet
            id="verify-file"
            label="Or create a file at this address that contains only the token"
            value={fileAddress(values.liveUrl.trim())}
            copyLabel="Copy address"
            disabled={disabled}
          />
          {token ? null : (
            <p className="text-[0.8125rem] text-muted-foreground">
              Enter or create a token to copy the tag.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
