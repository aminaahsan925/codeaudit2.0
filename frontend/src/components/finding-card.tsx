"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { Markdown } from "@/components/markdown";
import { SeverityBadge } from "@/components/severity-badge";
import type { Evidence, Finding, HttpEvidence, TraceStep } from "@/lib/api";
import { resolveScreenshotUrl } from "@/lib/artifacts";
import {
  AI_VERDICT_LABEL,
  CATEGORY_LABEL,
  CONFIDENCE_LABEL,
  ENGINE_LABEL,
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

function TraceList({ trace }: { trace: TraceStep[] }) {
  if (trace.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold">Data flow</h4>
      <ol className="flex flex-col gap-2 border-l-2 border-border pl-4">
        {trace.map((step, index) => (
          <li key={`${step.file}:${step.line}:${index}`} className="flex flex-col gap-1">
            <p className="text-sm">
              <span className="font-medium">{step.label}</span>{" "}
              <span className="font-mono text-xs text-muted-foreground">
                {step.file}:{step.line}
              </span>
            </p>
            <code className="block overflow-x-auto rounded-sm bg-muted px-2 py-1.5 font-mono text-xs whitespace-pre">
              {step.snippet}
            </code>
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
    <div className="flex flex-col gap-1">
      <h5 className="text-xs font-semibold text-muted-foreground">{title}</h5>
      <dl className="overflow-x-auto rounded-sm bg-muted px-2 py-1.5 font-mono text-xs">
        {entries.map(([name, value]) => (
          <div key={name} className="flex gap-2 py-0.5">
            <dt className="shrink-0 text-muted-foreground">{name}:</dt>
            <dd className="break-all">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function HttpEvidenceView({ http }: { http: HttpEvidence }) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold">Live request</h4>
      <p className="font-mono text-xs break-all">
        <span className="font-semibold">{http.method}</span> {http.url}{" "}
        <span className="text-muted-foreground">({http.status})</span>
      </p>
      <HeadersTable title="Request headers" headers={http.request_headers} />
      <HeadersTable title="Response headers" headers={http.response_headers} />
      {http.body_excerpt ? (
        <pre className="overflow-x-auto rounded-sm bg-muted px-2 py-1.5 font-mono text-xs whitespace-pre-wrap break-all">
          {http.body_excerpt}
        </pre>
      ) : null}
    </div>
  );
}

function EvidenceView({
  evidence,
  runId,
}: {
  evidence: Evidence;
  runId: string;
}) {
  const screenshotUrl = resolveScreenshotUrl(runId, evidence.screenshot_url);
  const hasAnything =
    Boolean(evidence.http) ||
    Boolean(evidence.package) ||
    Boolean(evidence.secret_preview) ||
    Boolean(evidence.notes) ||
    screenshotUrl !== null;
  if (!hasAnything) return null;

  return (
    <div className="flex flex-col gap-4">
      {evidence.http ? <HttpEvidenceView http={evidence.http} /> : null}
      {evidence.package ? (
        <div className="flex flex-col gap-1">
          <h4 className="text-sm font-semibold">Package</h4>
          <p className="font-mono text-xs">
            {evidence.package.name} {evidence.package.version}
          </p>
          <p className="text-xs text-muted-foreground">
            Advisory: {evidence.package.advisory}
          </p>
        </div>
      ) : null}
      {evidence.secret_preview ? (
        <div className="flex flex-col gap-1">
          <h4 className="text-sm font-semibold">Secret preview</h4>
          <code className="block w-fit rounded-sm bg-muted px-2 py-1 font-mono text-xs">
            {evidence.secret_preview}
          </code>
          <p className="text-xs text-muted-foreground">
            Only the first characters are shown; the full secret is never displayed.
          </p>
        </div>
      ) : null}
      {evidence.notes ? (
        <div className="flex flex-col gap-1">
          <h4 className="text-sm font-semibold">Notes</h4>
          <p className="text-sm">{evidence.notes}</p>
        </div>
      ) : null}
      {screenshotUrl ? (
        <div className="flex flex-col gap-1">
          <h4 className="text-sm font-semibold">Screenshot</h4>
          {/* Plain img: the screenshot lives on the API origin, and next/image
              would fetch it server-side instead of from the browser. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={screenshotUrl}
            alt="Screenshot captured during the audit"
            loading="lazy"
            className="max-w-full rounded-md border"
          />
        </div>
      ) : null}
    </div>
  );
}

/**
 * One finding in fix-first order. The header always shows the severity,
 * title and location; the proof (snippet, trace, evidence, AI verdict,
 * fix guidance) expands underneath.
 */
export function FindingCard({
  finding,
  index,
  runId,
  defaultOpen = false,
}: {
  finding: Finding;
  /** 1-based position in the fix-first list. */
  index: number;
  runId: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const location = findingLocation(finding);
  const panelId = `finding-${finding.id}`;

  return (
    <li className="overflow-hidden rounded-lg border bg-card">
      <div className="flex items-start gap-3 px-4 py-3 sm:px-5">
        <span
          aria-hidden="true"
          className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border font-mono text-xs font-semibold text-muted-foreground"
        >
          {index}
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <span className="text-xs text-muted-foreground">
              {CATEGORY_LABEL[finding.category]} · {ENGINE_LABEL[finding.engine]}
            </span>
          </div>
          <h3 className="text-base leading-snug font-semibold">{finding.title}</h3>
          {location ? (
            <p className="truncate font-mono text-xs text-muted-foreground">
              {location}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((value) => !value)}
          className="flex shrink-0 items-center gap-1 rounded-md border border-input px-2 py-1.5 text-xs font-medium hover:bg-muted"
        >
          {open ? "Hide proof" : "Show proof"}
          <ChevronDown
            aria-hidden="true"
            className={cn("size-3.5 transition-transform", open && "rotate-180")}
          />
        </button>
      </div>

      {open ? (
        <div
          id={panelId}
          className="flex flex-col gap-5 border-t px-4 py-4 sm:px-5"
        >
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
            <div className="flex gap-1.5">
              <dt className="font-medium text-foreground">Rule</dt>
              <dd className="font-mono">{finding.rule_id}</dd>
            </div>
            {finding.cwe ? (
              <div className="flex gap-1.5">
                <dt className="font-medium text-foreground">CWE</dt>
                <dd className="font-mono">{finding.cwe}</dd>
              </div>
            ) : null}
            <div className="flex gap-1.5">
              <dt className="font-medium text-foreground">Confidence</dt>
              <dd>{CONFIDENCE_LABEL[finding.confidence]}</dd>
            </div>
          </dl>

          {finding.snippet ? (
            <div className="flex flex-col gap-1">
              <h4 className="text-sm font-semibold">Code</h4>
              <pre className="overflow-x-auto rounded-md bg-muted px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre-wrap break-all">
                {finding.snippet}
              </pre>
            </div>
          ) : null}

          <TraceList trace={finding.trace} />
          <EvidenceView evidence={finding.evidence} runId={runId} />

          {finding.ai_verdict ? (
            <div className="flex flex-col gap-1 rounded-md border bg-muted/50 px-3 py-2">
              <h4 className="text-sm font-semibold">
                Review: {AI_VERDICT_LABEL[finding.ai_verdict.verdict]}
              </h4>
              <p className="text-sm">{finding.ai_verdict.reason}</p>
              {finding.ai_verdict.quoted_code ? (
                <code className="block overflow-x-auto rounded-sm bg-muted px-2 py-1.5 font-mono text-xs whitespace-pre">
                  {finding.ai_verdict.quoted_code}
                </code>
              ) : null}
            </div>
          ) : null}

          {finding.fix_guidance ? (
            <div className="flex flex-col gap-2">
              <h4 className="text-sm font-semibold">How to fix it</h4>
              <Markdown text={finding.fix_guidance} />
            </div>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
