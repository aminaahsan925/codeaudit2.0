"use client";

import { ChevronDown, CircleCheck } from "lucide-react";
import { useState } from "react";

import { findingLocation } from "@/components/finding-card";
import { findingLead, problemCount } from "@/components/report/finding-copy";
import { SeverityBadge } from "@/components/severity-badge";
import type { Finding } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Findings from the previous run that this run no longer finds. Collapsed by default. */
export function FixedFindings({ findings }: { findings: Finding[] }) {
  const [open, setOpen] = useState(false);
  if (findings.length === 0) return null;
  const panelId = "fixed-findings-list";

  return (
    <section
      aria-labelledby="fixed-heading"
      className="overflow-hidden rounded-2xl border border-verdict-launch/30 bg-card shadow-xs"
    >
      <div className="flex items-center gap-3 px-4 py-3.5 sm:px-5">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-verdict-launch-tint text-verdict-launch">
          <CircleCheck aria-hidden="true" className="size-4" />
        </span>
        <div className="flex min-w-0 flex-col">
          <h2 id="fixed-heading" className="text-base">
            Fixed since the last run
          </h2>
          <p className="text-sm text-muted-foreground">
            {problemCount(findings.length)} from the last run{" "}
            {findings.length === 1 ? "no longer shows up." : "no longer show up."}
          </p>
        </div>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((value) => !value)}
          className="ml-auto flex h-8 shrink-0 items-center gap-1 rounded-lg px-2.5 text-sm font-medium text-brand-fg transition-colors hover:bg-brand-soft"
        >
          {open ? "Hide" : "Show"}{" "}
          <span className="sr-only">fixed problems</span>
          <ChevronDown
            aria-hidden="true"
            className={cn("size-4 transition-transform duration-200", open && "rotate-180")}
          />
        </button>
      </div>
      {open ? (
        <ul
          id={panelId}
          className="flex animate-in flex-col divide-y border-t duration-200 fade-in-0"
        >
          {findings.map((finding) => {
            const location = findingLocation(finding);
            return (
              <li key={finding.id} className="flex flex-col gap-1 px-4 py-3 sm:px-5 sm:pl-15">
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={finding.severity} />
                  <span className="text-sm font-medium">{findingLead(finding)}</span>
                </div>
                <p className="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
                  <span>{finding.title}</span>
                  {location ? <span className="font-mono">{location}</span> : null}
                </p>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
