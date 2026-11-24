import type { components } from "@/types/api";

import { apiClient, apiRequest, type RequestOptions } from "./client";

export type Finding = components["schemas"]["Finding"];
export type FindingUpdate = components["schemas"]["FindingUpdate"];
export type TrackingStatus = components["schemas"]["TrackingStatus"];

/**
 * PATCH /api/runs/{run_id}/findings/{finding_id}: assign a finding and
 * track its fix. Both fields are optional; only the fields sent change.
 * An empty assignee clears the assignment.
 */
export async function updateFinding(
  runId: string,
  findingId: string,
  payload: FindingUpdate,
  options?: RequestOptions,
): Promise<Finding> {
  return apiRequest(
    ({ signal }) =>
      apiClient.PATCH("/api/runs/{run_id}/findings/{finding_id}", {
        signal,
        params: { path: { run_id: runId, finding_id: findingId } },
        body: payload,
      }),
    options,
  );
}
