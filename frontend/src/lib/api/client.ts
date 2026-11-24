import createClient from "openapi-fetch";

import { env } from "@/lib/env";
import { getSessionToken } from "@/lib/session";
import type { paths } from "@/types/api";

import {
  ApiError,
  apiErrorFromResponse,
  apiErrorFromThrown,
} from "./errors";

export const DEFAULT_TIMEOUT_MS = 10_000;

/** Low-level typed client. Prefer the per-resource helpers (e.g. getHealth). */
export const apiClient = createClient<paths>({
  baseUrl: env.NEXT_PUBLIC_API_BASE_URL,
  headers: { Accept: "application/json" },
  credentials: "omit",
  // Resolve fetch per call so tests and instrumentation can replace it.
  fetch: (request: Request) => globalThis.fetch(request),
});

/**
 * Sends the stored session token as Authorization: Bearer when one exists.
 * Anonymous requests (guest runs, public endpoints) go out without a header.
 */
apiClient.use({
  onRequest({ request }) {
    const token = getSessionToken();
    if (token !== null) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
});

type FetchResult<TData> = Promise<{
  data?: TData;
  error?: unknown;
  response: Response;
}>;

export interface RequestOptions {
  /** Caller cancellation (e.g. the signal TanStack Query passes to queryFn). */
  signal?: AbortSignal;
  timeoutMs?: number;
}

/**
 * Runs one openapi-fetch call with a timeout and returns its data, or throws
 * an ApiError with `{ code, message }` for any failure.
 */
export async function apiRequest<TData>(
  call: (init: { signal: AbortSignal }) => FetchResult<TData>,
  { signal, timeoutMs = DEFAULT_TIMEOUT_MS }: RequestOptions = {},
): Promise<TData> {
  const timeout = AbortSignal.timeout(timeoutMs);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;

  let result: Awaited<FetchResult<TData>>;
  try {
    result = await call({ signal: combined });
  } catch (error) {
    throw apiErrorFromThrown(error, {
      timedOut: timeout.aborted && !signal?.aborted,
    });
  }

  const { data, error, response } = result;
  if (!response.ok || error !== undefined) {
    throw apiErrorFromResponse(error, response);
  }
  if (data === undefined) {
    throw new ApiError(
      "invalid_response",
      "The API returned an empty response.",
      { status: response.status },
    );
  }
  return data;
}
