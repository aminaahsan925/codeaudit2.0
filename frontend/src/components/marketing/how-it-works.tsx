import { CircleCheck, FileArchive, Link2 } from "lucide-react";
import type { ReactNode } from "react";

import { SeverityMark } from "@/components/severity-badge";
import { RevealGroup, RevealItem } from "@/components/ui/reveal";
import { VerdictBadge } from "@/components/verdict-badge";
import { SEVERITIES, SEVERITY_LABEL, formatRiskScore } from "@/lib/report";
import { SAMPLE_COUNTS, SAMPLE_PROJECT, SAMPLE_SCORE, SAMPLE_VERDICT } from "@/lib/sample-data";
import { cn } from "@/lib/utils";

import { SectionIntro } from "./section-intro";

/** A fake, non-interactive field for the step illustrations. */
function FakeField({ prefix, children }: { prefix?: string; children: ReactNode }) {
  return (
    <div className="flex h-10 items-center gap-1 overflow-hidden rounded-[10px] border border-input/60 bg-card px-3 text-sm shadow-xs">
      {prefix && <span className="text-muted-foreground">{prefix}</span>}
      <span className="truncate">{children}</span>
    </div>
  );
}

function CodeStepVisual() {
  return (
    <div className="flex flex-col gap-3">
      <div className="inline-flex w-fit gap-1 rounded-[10px] bg-sunken p-1 text-xs font-medium">
        <span className="inline-flex h-7 items-center gap-1.5 rounded-md bg-card px-2.5 shadow-xs">
          <Link2 aria-hidden="true" className="size-3.5" />
          GitHub link
        </span>
        <span className="inline-flex h-7 items-center gap-1.5 px-2.5 text-muted-foreground">
          <FileArchive aria-hidden="true" className="size-3.5" />
          Zip file
        </span>
      </div>
      <FakeField prefix="github.com/you/">{SAMPLE_PROJECT.name}</FakeField>
    </div>
  );
}

function SiteStepVisual() {
  return (
    <div className="flex flex-col gap-3">
      <FakeField prefix="https://">{SAMPLE_PROJECT.url}</FakeField>
      <span className="inline-flex h-7 w-fit items-center gap-1.5 rounded-md border border-verdict-launch/45 bg-verdict-launch-tint px-2.5 text-xs font-semibold text-verdict-launch-fg">
        <CircleCheck aria-hidden="true" className="size-3.5 text-verdict-launch" />
        You own this site
      </span>
    </div>
  );
}

function ReportStepVisual() {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <VerdictBadge verdict={SAMPLE_VERDICT} />
        <p className="text-sm">
          <span className="font-semibold tabular-nums">{formatRiskScore(SAMPLE_SCORE)}</span>{" "}
          <span className="text-muted-foreground">risk score</span>
        </p>
      </div>
      <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
        {SEVERITIES.map((severity) => (
          <li key={severity} className="flex items-center gap-2">
            <SeverityMark severity={severity} className={cn("size-3", `[--mark:var(--sev-${severity})]`)} />
            <span className="text-muted-foreground">{SEVERITY_LABEL[severity]}</span>
            <span className="font-semibold tabular-nums">{SAMPLE_COUNTS[severity]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const STEPS = [
  {
    title: "Add your code",
    body: "Paste a GitHub link or upload a zip file. We read it and never run it.",
    visual: <CodeStepVisual />,
  },
  {
    title: "Add your live site",
    body: "Optional. Prove the site is yours with a small file, and we check it the way a visitor would.",
    visual: <SiteStepVisual />,
  },
  {
    title: "Read your report",
    body: "You get a verdict, a risk score and a fix-first list. Each problem has its proof and a suggested fix.",
    visual: <ReportStepVisual />,
  },
] as const;

export function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-title" className="scroll-mt-20 py-24 sm:py-28">
      <div className="container-page">
        <SectionIntro id="how-title" title="How an audit works">
          Three steps, and only the first one is required.
        </SectionIntro>
        <RevealGroup as="ol" className="mt-12 grid grid-cols-1 gap-5 lg:grid-cols-3">
          {STEPS.map((step, index) => (
            <RevealItem as="li" key={step.title} className="flex min-w-0">
              <div className="flex w-full flex-col overflow-hidden rounded-2xl border bg-card shadow-card">
                <div aria-hidden="true" className="flex min-h-40 flex-col justify-center border-b bg-sunken/60 p-6">
                  {step.visual}
                </div>
                <div className="flex gap-4 p-6">
                  <span
                    aria-hidden="true"
                    className="flex size-8 shrink-0 items-center justify-center rounded-full bg-brand-soft font-display text-sm font-semibold text-brand-fg tabular-nums"
                  >
                    {index + 1}
                  </span>
                  <div className="flex flex-col gap-1.5">
                    <h3 className="text-xl leading-8">
                      <span className="sr-only">Step {index + 1}: </span>
                      {step.title}
                    </h3>
                    <p className="text-muted-foreground">{step.body}</p>
                  </div>
                </div>
              </div>
            </RevealItem>
          ))}
        </RevealGroup>
      </div>
    </section>
  );
}
