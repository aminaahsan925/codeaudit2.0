import { InfoTip } from "@/components/ui/info-tip";
import { TERMS } from "@/lib/glossary";

import { describedBy, FieldError, FieldHint, FieldLabel, inputClasses } from "./field";
import type { StepFieldProps } from "./steps";

export function TestLoginStep({ values, errors, onChange, onBlur, disabled }: StepFieldProps) {
  const needsLiveSite = values.liveUrl.trim() === "" || values.domainToken.trim() === "";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2 text-sm text-muted-foreground">
        <p className="flex items-center gap-1">
          <span>We sign up, log in and walk through your app as this user.</span>
          <InfoTip term={TERMS.journey.term}>{TERMS.journey.plain}</InfoTip>
        </p>
        <p>
          Use a test account, not your own. We use it once for this audit and never store the
          password.
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <FieldLabel htmlFor="journey-email">Test account email</FieldLabel>
          <input
            id="journey-email"
            type="email"
            autoComplete="off"
            spellCheck={false}
            value={values.journeyEmail}
            onChange={(event) => onChange("journeyEmail", event.target.value)}
            onBlur={() => onBlur("journeyEmail")}
            aria-invalid={Boolean(errors.journeyEmail)}
            aria-describedby={describedBy(errors.journeyEmail && "journey-email-error")}
            disabled={disabled}
            placeholder="tester@example.com"
            className={inputClasses}
          />
          <FieldError id="journey-email-error" message={errors.journeyEmail} />
        </div>
        <div className="flex flex-col gap-1.5">
          <FieldLabel htmlFor="journey-password">Test account password</FieldLabel>
          <input
            id="journey-password"
            type="password"
            autoComplete="off"
            value={values.journeyPassword}
            onChange={(event) => onChange("journeyPassword", event.target.value)}
            onBlur={() => onBlur("journeyPassword")}
            aria-invalid={Boolean(errors.journeyPassword)}
            aria-describedby={describedBy(errors.journeyPassword && "journey-password-error")}
            disabled={disabled}
            className={inputClasses}
          />
          <FieldError id="journey-password-error" message={errors.journeyPassword} />
        </div>
      </div>

      {needsLiveSite ? (
        <FieldHint id="journey-needs-live">
          The test login only runs on a live site you have proved is yours. You can add one in
          the Live site step.
        </FieldHint>
      ) : null}
    </div>
  );
}
