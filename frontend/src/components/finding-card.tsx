"use client";

import { Tabs } from "@base-ui/react/tabs";
import {
  ChevronDown,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  type LucideIcon,
} from "lucide-react";
import type { Variants } from "motion/react";
import * as m from "motion/react-m";
import { useState } from "react";

import { Markdown } from "@/components/markdown";
import { CodeBlock } from "@/components/report/code-block";
import { findingLead, findingTerm } from "@/components/report/finding-copy";
import { SeverityBadge } from "@/components/severity-badge";
import { InfoTip } from "@/components/ui/info-tip";
import type { Evidence, Finding, HttpEvidence, TraceStep } from "@/lib/api";
import { resolveScreenshotUrl } from "@/lib/artifacts";
import { SEVERITY_PLAIN, TERMS } from "@/lib/glossary";
import {
  AI_VERDICT_LABEL,
  CONFIDENCE_LABEL,
  ENGINE_LABEL,
  SEVERITY_LABEL,
  type AIVerdictLabel,
} from "@/lib/report";
import { cn } from "@/lib/utils";

/** "src/lib/db.ts:4" or "src/lib/db.ts:4-6"; null when the finding has no file. */
export function findingLocation(finding: Finding): string | null {
  if (!finding.file) return null;
  if (finding.start_line === null) return finding.file;
  if (finding.end_line !== null && finding.end_line !== finding.start_line) {
    return `${finding.file}:${finding.start_line}-${finding.end_line}`;
  }
  return `${finding.file}:${finding.start_line}`;
}

const subheading = "text-sm font-semibold text-foreground";

function TraceList({ trace }: { trace: TraceStep[] }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-1">
        <h4 className={subheading}>Data flow</h4>
        <InfoTip term={TERMS.trace.term}>{TERMS.trace.plain}</InfoTip>
      </div>
      <ol className="flex flex-col">
        {trace.map((step, index) => (
          <li
            key={`${step.file}:${step.line}:${index}`}
            className="relative grid grid-cols-[1.5rem_minmax(0,1fr)] gap-x-3 pb-4 last:pb-0"
          >
            {index < trace.length - 1 ? (
              <span
                aria-hidden="true"
                className="absolute top-7 bottom-1 left-3 w-px -translate-x-1/2 bg-border"
              />
            ) : null}
            <span
              aria-hidden="true"
              className="flex size-6 items-center justify-center rounded-full border bg-card font-mono text-[0.6875rem] font-semibold text-muted-foreground tabular-nums"
            >
              {index + 1}
            </span>
            <div className="flex min-w-0 flex-col gap-1.5">
              <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
                <span className="font-medium">{step.label}</span>
                <span className="font-mono text-xs break-all text-muted-foreground">
                  {step.file}:{step.line}
                </span>
              </p>
              <CodeBlock code={step.snippet} startLine={step.line} />
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function HeadersTable({
  title,
  headers,
}: {
  title: string;
  headers: Record<string, string>;
}) {
  const entries = Object.entries(headers);
  if (entries.length === 0) return null;
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <h5 className="text-xs font-medium text-muted-foreground">{title}</h5>
      <dl className="flex flex-col gap-0.5 font-mono text-xs">
        {entries.map(([name, value]) => (
          <div key={name} className="flex min-w-0 gap-2">
            <dt className="shrink-0 text-muted-foreground">{name}:</dt>
            <dd className="min-w-0 break-all">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function HttpEvidenceView({ http }: { http: HttpEvidence }) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className={subheading}>Live request</h4>
      <div className="overflow-hidden rounded-xl border bg-sunken">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b px-3 py-2 font-mono text-xs">
          <span className="font-semibold">{http.method}</span>
          <span className="min-w-0 break-all">{http.url}</span>
          <span className="ml-auto rounded-sm border bg-card px-1.5 py-0.5 text-muted-foreground">
            Status {http.status}
          </span>
        </p>
        <div className="grid gap-4 px-3 py-3 sm:grid-cols-2">
          <HeadersTable title="Request headers" headers={http.request_headers} />
          <HeadersTable title="Response headers" headers={http.response_headers} />
        </div>
        {http.body_excerpt ? (
          <div className="border-t px-3 py-3">
            <h5 className="mb-1.5 text-xs font-medium text-muted-foreground">
              Response body
            </h5>
            <pre className="overflow-x-auto font-mono text-xs leading-5 break-all whitespace-pre-wrap">
              {http.body_excerpt}
            </pre>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function hasEvidence(evidence: Evidence, screenshotUrl: string | null): boolean {
  return (
    Boolean(evidence.http) ||
    Boolean(evidence.package) ||
    Boolean(evidence.secret_preview) ||
    Boolean(evidence.notes) ||
    screenshotUrl !== null
  );
}

function EvidenceView({
  evidence,
  screenshotUrl,
}: {
  evidence: Evidence;
  screenshotUrl: string | null;
}) {
  return (
    <>
      {evidence.http ? <HttpEvidenceView http={evidence.http} /> : null}
      {evidence.package ? (
        <div className="flex flex-col gap-1">
          <h4 className={subheading}>Package</h4>
          <p className="font-mono text-xs">
            {evidence.package.name} {evidence.package.version}
          </p>
          <p className="text-xs text-muted-foreground">
            Advisory: {evidence.package.advisory}
          </p>
        </div>
      ) : null}
      {evidence.secret_preview ? (
        <div className="flex flex-col gap-1.5">
          <h4 className={subheading}>Secret preview</h4>
          <code className="block w-fit rounded-md border bg-sunken px-2 py-1 font-mono text-xs">
            {evidence.secret_preview}
          </code>
          <p className="text-xs text-muted-foreground">
            Only the first characters are shown. The full secret is never displayed.
          </p>
        </div>
      ) : null}
      {evidence.notes ? (
        <div className="flex flex-col gap-1">
          <h4 className={subheading}>Notes</h4>
          <p className="text-sm">{evidence.notes}</p>
        </div>
      ) : null}
      {screenshotUrl ? (
        <div className="flex flex-col gap-1.5">
          <h4 className={subheading}>Screenshot</h4>
          {/* Plain img: the screenshot lives on the API origin, and next/image
              would fetch it server-side instead of from the browser. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={screenshotUrl}
            alt="Screenshot captured during the audit"
            loading="lazy"
            className="max-w-full rounded-xl border"
          />
        </div>
      ) : null}
    </>
  );
}

const REVIEW_ICON: Record<AIVerdictLabel, { icon: LucideIcon; tone: string }> = {
  confirmed: { icon: ShieldAlert, tone: "text-sev-critical" },
  needs_review: { icon: ShieldQuestion, tone: "text-sev-medium" },
  likely_false_positive: { icon: ShieldCheck, tone: "text-verdict-launch" },
};

type ProofTab = "evidence" | "trace" | "fix" | "review";

const TAB_LABEL: Record<ProofTab, string> = {
  evidence: "Evidence",
  trace: "Trace",
  fix: "How to fix",
  review: "Review note",
};

/**
 * One finding in fix-first order. The header leads with what can happen in
 * plain words, then the technical name, CWE and location. The proof
 * (evidence, trace, fix guidance, review note) opens underneath in tabs.
 *
 * Renders an `m.li` so a staggering parent list can animate it in; on its
 * own it renders in its final state.
 */
export function FindingCard({
  finding,
  index,
  runId,
  defaultOpen = false,
  variants,
}: {
  finding: Finding;
  /** 1-based position in the fix-first list. */
  index: number;
  runId: string;
  defaultOpen?: boolean;
  /** Entry animation from a staggering parent list. */
  variants?: Variants;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const location = findingLocation(finding);
  const panelId = `finding-${finding.id}`;
  const screenshotUrl = resolveScreenshotUrl(runId, finding.evidence.screenshot_url);
  const showEvidence = Boolean(finding.snippet) || hasEvidence(finding.evidence, screenshotUrl);

  const tabs: ProofTab[] = [];
  if (showEvidence) tabs.push("evidence");
  if (finding.trace.length > 0) tabs.push("trace");
  if (finding.fix_guidance) tabs.push("fix");
  if (finding.ai_verdict) tabs.push("review");

  const review = finding.ai_verdict ? REVIEW_ICON[finding.ai_verdict.verdict] : null;
  const ReviewIcon = review?.icon;

  return (
    <m.li
      variants={variants}
      className="overflow-hidden rounded-2xl border bg-card shadow-xs"
    >
      <div className="flex flex-col gap-2 p-4 sm:p-5">
        <div className="flex items-center gap-2 sm:gap-4">
          <span
            aria-hidden="true"
            className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-sunken font-mono text-xs font-semibold text-muted-foreground tabular-nums"
          >
            {index}
          </span>
          <span className="flex items-center gap-0.5">
            <SeverityBadge severity={finding.severity} />
            <InfoTip term={`${SEVERITY_LABEL[finding.severity]} severity`}>
              {SEVERITY_PLAIN[finding.severity]}
            </InfoTip>
          </span>
          <button
            type="button"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((value) => !value)}
            className="ml-auto flex h-8 shrink-0 items-center gap-1 rounded-lg px-2.5 text-sm font-medium text-brand-fg transition-colors hover:bg-brand-soft aria-expanded:bg-brand-soft"
          >
            {open ? "Hide proof" : "Show proof"}
            <ChevronDown
              aria-hidden="true"
              className={cn("size-4 transition-transform duration-200", open && "rotate-180")}
            />
          </button>
        </div>
        <div className="flex min-w-0 flex-col gap-2 sm:pl-11">
          <h3 className="text-lg leading-snug text-pretty">{findingLead(finding)}</h3>
          <p className="text-sm text-muted-foreground">{finding.title}</p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
            <span className="flex items-center gap-0.5 font-medium text-foreground">
              {findingTerm(finding)}
              {finding.cwe ? (
                <InfoTip term={TERMS.cwe.term}>{TERMS.cwe.plain}</InfoTip>
              ) : null}
            </span>
            {location ? (
              <span className="min-w-0 truncate font-mono">{location}</span>
            ) : null}
            <span>{ENGINE_LABEL[finding.engine]}</span>
          </div>
        </div>
      </div>

      {open ? (
        <div
          id={panelId}
          className="animate-in border-t duration-200 fade-in-0 slide-in-from-top-1"
        >
          {tabs.length > 0 ? (
            <Tabs.Root defaultValue={tabs[0]}>
              <div className="flex items-center gap-2 border-b px-2 sm:px-3">
                <Tabs.List
                  aria-label="Proof for this problem"
                  className="flex min-w-0 gap-1 overflow-x-auto"
                >
                  {tabs.map((tab) => (
                    <Tabs.Tab
                      key={tab}
                      value={tab}
                      className="relative h-11 shrink-0 rounded-md px-3 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors after:absolute after:inset-x-2 after:-bottom-px after:h-0.5 after:rounded-full hover:text-foreground data-active:text-foreground data-active:after:bg-brand"
                    >
                      {TAB_LABEL[tab]}
                    </Tabs.Tab>
                  ))}
                </Tabs.List>
                <InfoTip term={TERMS.evidence.term} className="mr-1 ml-auto">
                  {TERMS.evidence.plain}
                </InfoTip>
              </div>

              <div className="px-4 py-4 sm:px-5 sm:py-5">
                <Tabs.Panel value="evidence" className="flex flex-col gap-5 outline-none">
                  {finding.snippet ? (
                    <div className="flex flex-col gap-2">
                      <h4 className={subheading}>Code</h4>
                      <CodeBlock
                        code={finding.snippet}
                        startLine={finding.start_line}
                        endLine={finding.end_line}
                        severity={finding.severity}
                        caption={finding.file}
                      />
                    </div>
                  ) : null}
                  <EvidenceView evidence={finding.evidence} screenshotUrl={screenshotUrl} />
                </Tabs.Panel>

                {finding.trace.length > 0 ? (
                  <Tabs.Panel value="trace" className="outline-none">
                    <TraceList trace={finding.trace} />
                  </Tabs.Panel>
                ) : null}

                {finding.fix_guidance ? (
                  <Tabs.Panel value="fix" className="outline-none">
                    <Markdown text={finding.fix_guidance} className="max-w-prose" />
                  </Tabs.Panel>
                ) : null}

                {finding.ai_verdict ? (
                  <Tabs.Panel value="review" className="flex flex-col gap-3 outline-none">
                    <h4 className={cn(subheading, "flex items-center gap-2")}>
                      {ReviewIcon ? (
                        <ReviewIcon aria-hidden="true" className={cn("size-4", review?.tone)} />
                      ) : null}
                      Review: {AI_VERDICT_LABEL[finding.ai_verdict.verdict]}
                    </h4>
                    <p className="max-w-prose text-sm">{finding.ai_verdict.reason}</p>
                    {finding.ai_verdict.quoted_code ? (
                      <blockquote className="flex flex-col gap-1.5">
                        <p className="text-xs text-muted-foreground">The reviewer quoted this code:</p>
                        <CodeBlock code={finding.ai_verdict.quoted_code} startLine={null} />
                      </blockquote>
                    ) : null}
                  </Tabs.Panel>
                ) : null}
              </div>
            </Tabs.Root>
          ) : (
            <p className="px-4 py-4 text-sm text-muted-foreground sm:px-5">
              No extra proof was recorded for this problem.
            </p>
          )}

          <dl className="flex flex-wrap gap-x-6 gap-y-1 border-t bg-sunken/60 px-4 py-2.5 text-xs text-muted-foreground sm:px-5">
            <div className="flex gap-1.5">
              <dt>Rule</dt>
              <dd className="font-mono text-foreground">{finding.rule_id}</dd>
            </div>
            <div className="flex gap-1.5">
              <dt className="sr-only">Confidence</dt>
              <dd>{CONFIDENCE_LABEL[finding.confidence]}</dd>
            </div>
          </dl>
        </div>
      ) : null}
    </m.li>
  );
}
