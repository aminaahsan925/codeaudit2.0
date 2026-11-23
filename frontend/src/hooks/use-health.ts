"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth, type ApiError, type Health } from "@/lib/api";

export const healthQueryKey = ["health"] as const;

export const HEALTH_REFETCH_INTERVAL_MS = 30_000;

/** Backend liveness, polled every 30 seconds while the page is visible. */
export function useHealth() {
  return useQuery<Health, ApiError>({
    queryKey: healthQueryKey,
    queryFn: ({ signal }) => getHealth({ signal, timeoutMs: 5_000 }),
    refetchInterval: HEALTH_REFETCH_INTERVAL_MS,
    retry: 1,
    staleTime: 10_000,
  });
}
