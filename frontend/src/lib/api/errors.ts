import { z } from "zod";

import type { components } from "@/types/api";

type BackendErrorCode = components["schemas"]["ErrorCode"];

/** Codes produced on the client when no backend error body is available. */
export type ClientErrorCode =
  | "network_error"
  | "timeout"
  | "aborted"
  | "http_error"
  | "invalid_response";

export type ApiErrorCode = BackendErrorCode | ClientErrorCode;

/**
 * Every failure from the typed client is normalised to this shape, mirroring
 * the backend's `{"error": {"code", "message"}}` envelope.
 */
export class ApiError extends Error {
  override name = "ApiError";
  readonly code: ApiErrorCode;
  /** HTTP status, or null when the request never got a response. */
  readonly status: number | null;

  constructor(
    code: ApiErrorCode,
    message: string,
    options: { status?: number | null; cause?: unknown } = {},
  ) {
    super(message, { cause: options.cause });
    this.code = code;
    this.status = options.status ?? null;
  }

  toJSON(): { code: ApiErrorCode; message: string } {
    return { code: this.code, message: this.message };
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string().min(1).max(64),
    message: z.string().min(1).max(500),
  }),
});

const backendCodes: ReadonlySet<string> = new Set<BackendErrorCode>([
  "bad_request",
  "unauthorized",
  "forbidden",
  "not_found",
  "method_not_allowed",
  "payload_too_large",
  "validation_error",
  "internal_error",
]);

function codeForStatus(status: number): ApiErrorCode {
  switch (status) {
    case 400:
      return "bad_request";
    case 401:
      return "unauthorized";
    case 403:
      return "forbidden";
    case 404:
      return "not_found";
    case 405:
      return "method_not_allowed";
    case 413:
      return "payload_too_large";
    case 422:
      return "validation_error";
    default:
      return status >= 500 ? "internal_error" : "http_error";
  }
}

/** Builds an ApiError from a non-2xx response body (already parsed by openapi-fetch). */
export function apiErrorFromResponse(
  body: unknown,
  response: Response,
): ApiError {
  const parsed = errorEnvelopeSchema.safeParse(body);
  if (parsed.success) {
    const { code, message } = parsed.data.error;
    return new ApiError(
      backendCodes.has(code) ? (code as BackendErrorCode) : codeForStatus(response.status),
      message,
      { status: response.status },
    );
  }
  return new ApiError(
    codeForStatus(response.status),
    `The API responded with status ${response.status}.`,
    { status: response.status },
  );
}

/** Converts anything thrown by fetch (network failure, abort, timeout) to an ApiError. */
export function apiErrorFromThrown(
  error: unknown,
  { timedOut }: { timedOut: boolean },
): ApiError {
  if (error instanceof ApiError) return error;
  if (timedOut) {
    return new ApiError("timeout", "The API did not respond in time.", {
      cause: error,
    });
  }
  // Compare by name: abort errors can come from a different realm's
  // DOMException class (e.g. Node vs. jsdom), which breaks instanceof.
  if (
    typeof error === "object" &&
    error !== null &&
    (error as { name?: unknown }).name === "AbortError"
  ) {
    return new ApiError("aborted", "The request was cancelled.", {
      cause: error,
    });
  }
  return new ApiError(
    "network_error",
    "Could not reach the LaunchAudit API. Check that it is running and reachable.",
    { cause: error },
  );
}
