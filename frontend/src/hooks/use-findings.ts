"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  updateFinding,
  type ApiError,
  type Finding,
  type FindingUpdate,
  type Report,
  type TrackingStatus,
} from "@/lib/api";

import { reportQueryKey } from "./use-report";

type FindingPatch = Partial<Pick<Finding, "assignee" | "tracking_status">>;

/**
 * Narrows a PATCH payload to the fields it actually sets. The generated
 * FindingUpdate types tracking_status as a plain string (the backend
 * validates it so it can answer 400), so the cast is where that looseness
 * is contained; callers only ever send one of the four statuses.
 */
function patchFor(payload: FindingUpdate): FindingPatch {
  const patch: FindingPatch = {};
  if (payload.assignee !== undefined) patch.assignee = payload.assignee;
  if (payload.tracking_status !== undefined && payload.tracking_status !== null) {
    patch.tracking_status = payload.tracking_status as TrackingStatus;
  }
  return patch;
}

function applyToReport(
  report: Report,
  findingId: string,
  patch: FindingPatch | Finding,
): Report {
  return {
    ...report,
    findings: report.findings.map((finding) =>
      finding.id === findingId ? { ...finding, ...patch } : finding,
    ),
  };
}

/**
 * Updates a finding's assignee and tracking status, optimistically patching
 * the cached report for this run so the row updates at once; the cache is
 * rolled back on failure and refetched once the request settles.
 */
export function useUpdateFinding(runId: string) {
  const queryClient = useQueryClient();
  const key = reportQueryKey(runId);
  return useMutation<
    Finding,
    ApiError,
    { findingId: string; payload: FindingUpdate },
    { previous: Report | undefined }
  >({
    mutationFn: ({ findingId, payload }) => updateFinding(runId, findingId, payload),
    onMutate: async ({ findingId, payload }) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<Report>(key);
      if (previous) {
        queryClient.setQueryData<Report>(
          key,
          applyToReport(previous, findingId, patchFor(payload)),
        );
      }
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(key, context.previous);
      }
    },
    onSuccess: (finding) => {
      const cached = queryClient.getQueryData<Report>(key);
      if (cached) {
        queryClient.setQueryData<Report>(
          key,
          applyToReport(cached, finding.id, finding),
        );
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: key });
    },
  });
}
