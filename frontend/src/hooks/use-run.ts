"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createRun,
  getRun,
  rerunRun,
  type ApiError,
  type AuditRun,
  type CreateRunInput,
  type RerunRequest,
} from "@/lib/api";
import { isActiveRunStatus } from "@/lib/report";
import { recordRun } from "@/lib/runs-history";

export const runQueryKey = (runId: string) => ["runs", runId] as const;

/** How often the run page re-checks while the audit is still going. */
export const RUN_POLL_INTERVAL_MS = 2_000;

/**
 * One audit run, polled every 2 seconds while it is queued or running.
 * Polling stops on its own once the run reaches a terminal status.
 */
export function useRun(runId: string | null) {
  return useQuery<AuditRun, ApiError>({
    queryKey: runQueryKey(runId ?? ""),
    queryFn: ({ signal }) => getRun(runId as string, { signal }),
    enabled: runId !== null,
    refetchInterval: (query) =>
      query.state.data && isActiveRunStatus(query.state.data.status)
        ? RUN_POLL_INTERVAL_MS
        : false,
  });
}

/** Starts an audit run and records it in this browser's history. */
export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation<AuditRun, ApiError, CreateRunInput>({
    mutationFn: (input) => createRun(input),
    onSuccess: (run) => {
      recordRun({ id: run.id, projectName: run.project_name });
      queryClient.setQueryData(runQueryKey(run.id), run);
    },
  });
}

/** Re-runs an audit after fixes and records the new run in history. */
export function useRerunRun() {
  const queryClient = useQueryClient();
  return useMutation<
    AuditRun,
    ApiError,
    { runId: string; payload?: RerunRequest }
  >({
    mutationFn: ({ runId, payload }) => rerunRun(runId, payload),
    onSuccess: (run) => {
      recordRun({ id: run.id, projectName: run.project_name });
      queryClient.setQueryData(runQueryKey(run.id), run);
    },
  });
}
