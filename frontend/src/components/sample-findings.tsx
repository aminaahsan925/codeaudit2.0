"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";

import { SeverityBadge } from "@/components/severity-badge";
import type { Severity } from "@/lib/report";
import {
  SAMPLE_FINDINGS,
  type ProofLine,
  type SampleFinding,
} from "@/lib/sample-report";
import { cn } from "@/lib/utils";

const flagTone: Record<Severity, string> = {
  critical: "bg-sev-critical-tint border-sev-critical text-sev-critical-fg",
  high: "bg-sev-high-tint border-sev-high text-sev-high-fg",
  medium: "bg-sev-medium-tint border-sev-medium text-sev-medium-fg",
  low: "bg-sev-low-tint border-sev-low text-sev-low-fg",
};

function ProofBlock({
  label,
  lines,
  severity,
  firstLine,
}: {
  label: string;
  lines: readonly ProofLine[];
  severity: Severity;
  firstLine?: number;
}) {
  return (
    <div
      role="region"
      aria-label={label}
      tabIndex={0}
      className="overflow-x-auto rounded-md border bg-muted/60 py-2 font-mono text-xs leading-6 focus-visible:outline-2 focus-visible:outline-ring"
    >
      <pre className="min-w-max">
        {lines.map((line, index) => (
          <span
            key={index}
            className={cn(
              "flex border-l-2 border-transparent pr-3",
              line.flagged && cn("font-semibold", flagTone[severity]),
            )}
          >
            {firstLine !== undefined ? (
              <span
                aria-hidden="true"
                className="w-9 shrink-0 pr-3 text-right text-muted-foreground select-none"
              >
                {firstLine + index}
              </span>
            ) : (
              <span aria-hidden="true" className="w-3 shrink-0" />
            )}
            <code>{line.text || " "}</code>
            {line.flagged ? <span className="sr-only"> (flagged)</span> : null}
          </span>
        ))}
      </pre>
    </div>
  );
}

function FindingProof({ finding }: { finding: SampleFinding }) {
  const { proof, severity } = finding;

  if (proof.kind === "code") {
    return (
      <div className="flex flex-col gap-3">
        <ProofBlock
          label={`Source excerpt from ${proof.file}`}
          lines={proof.lines}
          severity={severity}
          firstLine={proof.firstLine}
        />
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">
            How the key reaches the browser
          </p>
          <ol className="flex flex-col gap-1">
            {proof.trace.map((step, index) => (
              <li key={step.where} className="flex items-baseline gap-2 text-xs">
                <span
                  aria-hidden="true"
                  className="flex size-4 shrink-0 items-center justify-center rounded-full border border-input text-[0.625rem] leading-none text-muted-foreground"
                >
                  {index + 1}
                </span>
                <span>
                  {step.label}{" "}
                  <span className="font-mono text-muted-foreground">{step.where}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    );
  }

  if (proof.kind === "http") {
    return (
      <div className="flex flex-col gap-2">
        <ProofBlock label="Request sent" lines={proof.request} severity={severity} />
        <ProofBlock label="Response received" lines={proof.response} severity={severity} />
        <p className="text-xs text-muted-foreground">{proof.note}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="font-mono text-xs text-muted-foreground">{proof.request}</p>
      <ProofBlock label="Response headers" lines={proof.headers} severity={severity} />
      <p className="text-xs text-muted-foreground">{proof.note}</p>
    </div>
  );
}

/**
 * Findings list for the sample report. One finding is open at a time and
 * opening one shows the proof attached to it.
 */
export function SampleFindings() {
  const [openId, setOpenId] = useState<string | null>(SAMPLE_FINDINGS[0]?.id ?? null);
  const baseId = useId();

  return (
    <ul className="flex flex-col divide-y">
      {SAMPLE_FINDINGS.map((finding) => {
        const open = openId === finding.id;
        const panelId = `${baseId}-${finding.id}`;
        return (
          <li key={finding.id} className="py-1 first:pt-0 last:pb-0">
            <button
              type="button"
              aria-expanded={open}
              aria-controls={panelId}
              onClick={() => setOpenId(open ? null : finding.id)}
              className="group -mx-2 grid w-[calc(100%+1rem)] cursor-pointer grid-cols-[1fr_auto] items-start gap-x-3 gap-y-1.5 rounded-md px-2 py-2.5 text-left hover:bg-muted/60 sm:grid-cols-[5.75rem_1fr_auto]"
            >
              <span className="col-start-1 row-start-1">
                <SeverityBadge severity={finding.severity} />
              </span>
              <span className="col-start-1 row-start-2 flex min-w-0 flex-col gap-1 sm:col-start-2 sm:row-start-1">
                <span className="text-sm leading-snug font-semibold">{finding.title}</span>
                <span className="text-xs text-muted-foreground">{finding.source}</span>
              </span>
              <ChevronDown
                aria-hidden="true"
                className="col-start-2 row-start-1 mt-0.5 size-4 text-muted-foreground transition-transform duration-200 group-aria-expanded:rotate-180 sm:col-start-3"
              />
            </button>
            <div
              id={panelId}
              inert={!open}
              className={cn(
                "grid transition-[grid-template-rows] duration-200 ease-out",
                open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
              )}
            >
              <div className="overflow-hidden">
                <div className="pt-1 pb-3">
                  <FindingProof finding={finding} />
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
