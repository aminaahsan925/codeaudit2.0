import type { components } from "@/types/api";

import { env } from "@/lib/env";

import { apiClient, apiRequest, type RequestOptions } from "./client";

export type Report = components["schemas"]["ReportResponse"];
export type Finding = components["schemas"]["Finding"];
export type JourneyStepView = components["schemas"]["JourneyStepView"];
export type FindingCategory = components["schemas"]["FindingCategory"];
export type FindingEngine = components["schemas"]["FindingEngine"];
export type FindingStatus = components["schemas"]["FindingStatus"];
export type Confidence = components["schemas"]["Confidence"];
export type AIVerdict = components["schemas"]["AIVerdict"];
export type AIVerdictLabel = components["schemas"]["AIVerdictLabel"];
export type TraceStep = components["schemas"]["TraceStep"];
export type Evidence = components["schemas"]["Evidence"];
export type HttpEvidence = components["schemas"]["HttpEvidence"];

/**
 * GET /api/runs/{run_id}/report: the full report for a run.
 *
 * This endpoint requires a bearer token. This build has no login UI, so
 * guest report pages resolve the report through the run's public share
 * token instead (see `useReport`); this helper stays for authenticated use.
 */
export async function getReport(
  runId: string,
  options?: RequestOptions,
): Promise<Report> {
  return apiRequest(
    ({ signal }) =>
      apiClient.GET("/api/runs/{run_id}/report", {
        signal,
        params: { path: { run_id: runId } },
      }),
    options,
  );
}

/** GET /api/reports/shared/{token}: the full report by share token (public). */
export async function getSharedReport(
  token: string,
  options?: RequestOptions,
): Promise<Report> {
  return apiRequest(
    ({ signal }) =>
      apiClient.GET("/api/reports/shared/{token}", {
        signal,
        params: { path: { token } },
      }),
    options,
  );
}

/** Frontend route for a public shared report. */
export function sharedReportPath(token: string): string {
  return `/r/${encodeURIComponent(token)}`;
}

/**
 * Direct link to the report PDF. The share token authorises the download,
 * so no bearer token is needed. Returns null without a token: the PDF
 * endpoint rejects anonymous requests.
 */
export function reportPdfUrl(runId: string, shareToken: string | null): string | null {
  if (!shareToken) return null;
  return (
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/runs/${encodeURIComponent(runId)}/report.pdf` +
    `?token=${encodeURIComponent(shareToken)}`
  );
}
