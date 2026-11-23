import { z } from "zod";

import type { components } from "@/types/api";

import { apiClient, apiRequest, type RequestOptions } from "./client";
import { ApiError } from "./errors";

export type Health = components["schemas"]["HealthResponse"];

const healthSchema = z.object({
  status: z.literal("ok"),
  version: z.string().min(1).max(64),
}) satisfies z.ZodType<Health>;

/** GET /api/health: public liveness check. */
export async function getHealth(options?: RequestOptions): Promise<Health> {
  const data = await apiRequest(
    ({ signal }) => apiClient.GET("/api/health", { signal }),
    options,
  );
  const parsed = healthSchema.safeParse(data);
  if (!parsed.success) {
    throw new ApiError(
      "invalid_response",
      "The API health response was not in the expected format.",
    );
  }
  return parsed.data;
}
