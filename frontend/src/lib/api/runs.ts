import type { components } from "@/types/api";

import { apiClient, apiRequest, type RequestOptions } from "./client";

export type AuditRun = components["schemas"]["AuditRun"];
export type AuditRunStatus = components["schemas"]["AuditRunStatus"];
export type RerunRequest = components["schemas"]["RerunRequest"];

/** Zip uploads need longer than the default 10s request timeout. */
export const CREATE_RUN_TIMEOUT_MS = 120_000;

export interface CreateRunInput {
  projectName: string;
  repoUrl?: string;
  liveUrl?: string;
  /** The zip to scan. Sent as multipart file part `zip_file`. */
  zipFile?: File | null;
  journeyEmail?: string;
  journeyPassword?: string;
  domainToken?: string;
}

function appendIfPresent(form: FormData, key: string, value: string | undefined) {
  const trimmed = value?.trim();
  if (trimmed) form.append(key, trimmed);
}

/**
 * POST /api/runs: start an audit run. Guests (no token) are accepted; the
 * run is owned by its link. Sends multipart/form-data: openapi-fetch passes
 * a FormData body through untouched and the browser sets the boundary.
 */
export async function createRun(
  input: CreateRunInput,
  options?: RequestOptions,
): Promise<AuditRun> {
  const form = new FormData();
  form.append("project_name", input.projectName.trim());
  appendIfPresent(form, "repo_url", input.repoUrl);
  appendIfPresent(form, "live_url", input.liveUrl);
  appendIfPresent(form, "journey_email", input.journeyEmail);
  appendIfPresent(form, "journey_password", input.journeyPassword);
  appendIfPresent(form, "domain_token", input.domainToken);
  if (input.zipFile) form.append("zip_file", input.zipFile);

  return apiRequest(
    ({ signal }) =>
      apiClient.POST("/api/runs", {
        signal,
        // The generated body type is the multipart schema object; a real
        // FormData instance is what openapi-fetch sends for this endpoint.
        body: form as unknown as components["schemas"]["Body_create_run_api_runs_post"],
      }),
    { ...options, timeoutMs: options?.timeoutMs ?? CREATE_RUN_TIMEOUT_MS },
  );
}

/** GET /api/runs/{run_id}: public by id, no token needed. */
export async function getRun(
  runId: string,
  options?: RequestOptions,
): Promise<AuditRun> {
  return apiRequest(
    ({ signal }) =>
      apiClient.GET("/api/runs/{run_id}", {
        signal,
        params: { path: { run_id: runId } },
      }),
    options,
  );
}

/**
 * POST /api/runs/{run_id}/rerun: re-run an audit after fixes. Guest runs
 * rerun without a token. Journey credentials and the domain token are never
 * persisted, so pass fresh ones in `payload` when the rerun should repeat
 * the journey or the live checks.
 */
export async function rerunRun(
  runId: string,
  payload?: RerunRequest,
  options?: RequestOptions,
): Promise<AuditRun> {
  return apiRequest(
    ({ signal }) =>
      apiClient.POST("/api/runs/{run_id}/rerun", {
        signal,
        params: { path: { run_id: runId } },
        ...(payload === undefined ? {} : { body: payload }),
      }),
    options,
  );
}
