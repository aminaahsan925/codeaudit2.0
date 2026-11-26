import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { AuditFormValues } from "@/lib/audit-form";

import { formatFileSize } from "./field";

function Row({
  term,
  children,
  stepLabel,
  onChange,
  disabled,
}: {
  term: string;
  children: ReactNode;
  stepLabel: string;
  onChange: () => void;
  disabled: boolean;
}) {
  return (
    <div className="flex items-start gap-4 py-3.5 first:pt-0 last:pb-0">
      <div className="flex min-w-0 flex-1 flex-col gap-0.5 sm:flex-row sm:gap-4">
        <dt className="shrink-0 text-sm text-muted-foreground sm:w-32">{term}</dt>
        <dd className="min-w-0 text-sm break-words text-foreground">{children}</dd>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onChange}
        disabled={disabled}
        className="-my-1 shrink-0 text-brand-fg"
      >
        Change<span className="sr-only"> {stepLabel}</span>
      </Button>
    </div>
  );
}

function Missing({ children }: { children: ReactNode }) {
  return <span className="text-muted-foreground">{children}</span>;
}

export function ReviewStep({
  values,
  onEdit,
  disabled,
}: {
  values: AuditFormValues;
  /** Opens a step by index. */
  onEdit: (index: number) => void;
  disabled: boolean;
}) {
  const repoUrl = values.repoUrl.trim();
  const liveUrl = values.liveUrl.trim();
  const token = values.domainToken.trim();
  const email = values.journeyEmail.trim();
  const liveChecks = liveUrl !== "" && token !== "";
  const testLogin = liveChecks && email !== "";

  const plan: string[] = [
    "We read your code and look for security problems. Nothing in it is installed or run.",
  ];
  if (liveChecks) {
    plan.push(
      `We check that the token is on ${liveUrl}, then look at what any visitor to the site can see.`,
    );
  } else if (liveUrl !== "") {
    plan.push("We skip the live site checks, because there is no token to prove the site is yours.");
  }
  if (testLogin) {
    plan.push(`We sign up and log in as ${email}, then forget the password.`);
  } else if (email !== "") {
    plan.push("We skip the test login, because it needs a live site you have proved is yours.");
  }
  plan.push("You get a report with a launch verdict and a list of what to fix first.");

  return (
    <div className="flex flex-col gap-8">
      <dl className="divide-y divide-border">
        <Row term="Project" stepLabel="project and code" onChange={() => onEdit(0)} disabled={disabled}>
          {values.projectName.trim()}
        </Row>
        <Row term="Code" stepLabel="code" onChange={() => onEdit(0)} disabled={disabled}>
          {values.zipFile ? (
            <>
              {values.zipFile.name}{" "}
              <span className="text-muted-foreground">({formatFileSize(values.zipFile.size)})</span>
            </>
          ) : (
            <span className="font-mono text-[0.8125rem]">{repoUrl}</span>
          )}
        </Row>
        <Row term="Live site" stepLabel="live site" onChange={() => onEdit(1)} disabled={disabled}>
          {liveUrl ? (
            <span className="flex flex-col gap-0.5">
              <span className="font-mono text-[0.8125rem]">{liveUrl}</span>
              <span className="text-muted-foreground">
                {token ? "Token added" : "No token, so live checks are skipped"}
              </span>
            </span>
          ) : (
            <Missing>Skipped. Only the code is checked.</Missing>
          )}
        </Row>
        <Row term="Test login" stepLabel="test login" onChange={() => onEdit(2)} disabled={disabled}>
          {email ? email : <Missing>Skipped</Missing>}
        </Row>
      </dl>

      <section aria-labelledby="plan-heading" className="flex flex-col gap-3">
        <h3 id="plan-heading" className="text-base">
          What happens when you run the audit
        </h3>
        <ol className="flex flex-col gap-2.5">
          {plan.map((line, index) => (
            <li key={line} className="flex gap-3 text-sm text-foreground">
              <span
                aria-hidden="true"
                className="flex size-5 shrink-0 items-center justify-center rounded-full bg-sunken text-[0.6875rem] font-semibold text-muted-foreground tabular-nums"
              >
                {index + 1}
              </span>
              <span>{line}</span>
            </li>
          ))}
        </ol>
        <p className="text-sm text-muted-foreground">
          No account needed. You open the report from its link, so keep the link safe.
        </p>
      </section>
    </div>
  );
}
