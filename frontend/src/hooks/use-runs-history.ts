"use client";

import { useQueries } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";

import {
  getRun,
  type ApiError,
  type AuditRun,
} from "@/lib/api";
import {
  getStoredRunsServerSnapshot,
  getStoredRunsSnapshot,
  subscribeToStoredRuns,
  type StoredRun,
} from "@/lib/runs-history";

import { runQueryKey } from "./use-run";

export interface HistoryEntry {
  stored: StoredRun;
  /** The live run, once its fetch has returned. */
  run: AuditRun | undefined;
  /** Whether this entry's run fetch is still going or failed. */
  isLoading: boolean;
  isError: boolean;
}

export interface RunsHistory {
  /**
   * Null until the client has mounted: the server renders no stored runs,
   * so the first client render must agree with it. After mount this is
   * the stored list (possibly empty), newest first.
   */
  entries: HistoryEntry[] | null;
}

/** True after hydration, false during server render and the first client render. */
function useMounted(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

/**
 * The history page's data: runs this browser created (localStorage),
 * newest first, each enriched with its live status from the public
 * GET /api/runs/{id} endpoint. The list updates live when a run is
 * recorded in this tab or another.
 */
export function useRunsHistory(): RunsHistory {
  const mounted = useMounted();
  const stored = useSyncExternalStore(
    subscribeToStoredRuns,
    getStoredRunsSnapshot,
    getStoredRunsServerSnapshot,
  );
  const visible = mounted ? stored : [];

  const queries = useQueries({
    queries: visible.map((entry) => ({
      queryKey: runQueryKey(entry.id),
      queryFn: ({ signal }: { signal: AbortSignal }) =>
        getRun(entry.id, { signal }),
      retry: (failureCount: number, error: unknown) => {
        // A run the API no longer knows (404) will not come back on retry.
        if (error instanceof Error && (error as ApiError).status === 404) {
          return false;
        }
        return failureCount < 1;
      },
    })),
  });

  const entries: HistoryEntry[] | null = mounted
    ? visible.map((entry, index) => {
        const query = queries[index];
        return {
          stored: entry,
          run: query?.data,
          isLoading: query?.isPending ?? false,
          isError: query?.isError ?? false,
        };
      })
    : null;

  return { entries };
}
