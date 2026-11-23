"use client";

import { useQuery } from "@tanstack/react-query";

import {
  ApiError,
  getRun,
  getSharedReport,
  type Report,
  type ApiError as ApiErrorType,
} from "@/lib/api";

export const reportQueryKey = (runId: string) => ["reports", "run", runId] as const;
export const sharedReportQueryKey = (token: string) =>
  ["reports", "shared", token] as const;

/**
 * The full report for a run, resolved the guest way.
 *
 * GET /api/runs/{id}/report needs a bearer token and this build has no
 * login UI, so the hook loads the run (public by id) and then fetches the
 * report through the run's public share token. The report payload carries
 * the run itself, so one query covers both.
 */
export function useReport(runId: string | null) {
  return useQuery<Report, ApiErrorType>({
    queryKey: reportQueryKey(runId ?? ""),
    queryFn: async ({ signal }) => {
      const run = await getRun(runId as string, { signal });
      if (!run.share_token) {
        throw new ApiError(
          "invalid_response",
          "This run has no share link yet, so its report cannot be opened.",
        );
      }
      return getSharedReport(run.share_token, { signal });
    },
    enabled: runId !== null,
  });
}

/** The full report behind a public share token (/r/[token]). */
export function useSharedReport(token: string | null) {
  return useQuery<Report, ApiErrorType>({
    queryKey: sharedReportQueryKey(token ?? ""),
    queryFn: ({ signal }) => getSharedReport(token as string, { signal }),
    enabled: token !== null,
  });
}
