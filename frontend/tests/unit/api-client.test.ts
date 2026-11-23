import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getHealth } from "@/lib/api";
import { apiErrorFromResponse } from "@/lib/api/errors";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubFetch(impl: (req: Request) => Promise<Response>) {
  const fn = vi.fn(impl);
  vi.stubGlobal("fetch", fn);
  return fn;
}

/**
 * Rejects like a browser fetch does on abort. Timeouts reject with the signal
 * reason; caller aborts reject with a DOMException from the global realm
 * (jsdom's DOMException differs from Node's, which backs AbortController).
 */
function neverResolving(req: Request): Promise<Response> {
  return new Promise((_, reject) => {
    req.signal.addEventListener("abort", () => {
      const reason: unknown = req.signal.reason;
      reject(
        reason instanceof Error && reason.name === "TimeoutError"
          ? reason
          : new DOMException("The operation was aborted.", "AbortError"),
      );
    });
  });
}

async function catchError(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (e) {
    expect(e).toBeInstanceOf(ApiError);
    return e as ApiError;
  }
  throw new Error("expected promise to reject");
}

afterEach(() => vi.unstubAllGlobals());

describe("getHealth", () => {
  it("parses a valid body and calls /api/health", async () => {
    const fetchMock = stubFetch(async () => json({ status: "ok", version: "0.1.0" }));
    await expect(getHealth()).resolves.toEqual({ status: "ok", version: "0.1.0" });
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe("/api/health");
    expect(req.method).toBe("GET");
    expect(req.credentials).toBe("omit");
  });

  it("turns a backend error envelope into an ApiError", async () => {
    stubFetch(async () =>
      json({ error: { code: "forbidden", message: "Not allowed here" } }, 403),
    );
    const err = await catchError(getHealth());
    expect(err.code).toBe("forbidden");
    expect(err.message).toBe("Not allowed here");
    expect(err.status).toBe(403);
    expect(err.toJSON()).toEqual({ code: "forbidden", message: "Not allowed here" });
  });

  it("maps an error without an envelope by status", async () => {
    stubFetch(async () => new Response("<html>oops</html>", { status: 503 }));
    const err = await catchError(getHealth());
    expect(err.code).toBe("internal_error");
    expect(err.status).toBe(503);
  });

  it("maps a network failure to network_error", async () => {
    stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    });
    const err = await catchError(getHealth());
    expect(err.code).toBe("network_error");
    expect(err.status).toBeNull();
  });

  it.each([
    [{ status: "down", version: "1" }],
    [{ status: "ok" }],
    [{ status: "ok", version: "" }],
    [{ nope: true }],
  ])("rejects an invalid body %j as invalid_response", async (body) => {
    stubFetch(async () => json(body));
    const err = await catchError(getHealth());
    expect(err.code).toBe("invalid_response");
  });

  it("rejects an empty 200 body as invalid_response", async () => {
    stubFetch(async () => new Response(null, { status: 200 }));
    const err = await catchError(getHealth());
    expect(err.code).toBe("invalid_response");
  });

  it("times out when fetch never resolves", async () => {
    stubFetch(async (req) => neverResolving(req));
    const err = await catchError(getHealth({ timeoutMs: 30 }));
    expect(err.code).toBe("timeout");
  });

  it("reports caller cancellation as aborted, not timeout", async () => {
    stubFetch(async (req) => neverResolving(req));
    const controller = new AbortController();
    const pending = catchError(
      getHealth({ signal: controller.signal, timeoutMs: 5_000 }),
    );
    controller.abort();
    const err = await pending;
    expect(err.code).toBe("aborted");
  });
});

describe("apiErrorFromResponse", () => {
  it.each([
    [400, "bad_request"],
    [401, "unauthorized"],
    [404, "not_found"],
    [413, "payload_too_large"],
    [422, "validation_error"],
    [500, "internal_error"],
    [418, "http_error"],
  ])("maps status %s to %s without a body", (status, code) => {
    const err = apiErrorFromResponse(undefined, new Response(null, { status }));
    expect(err.code).toBe(code);
    expect(err.status).toBe(status);
  });

  it("falls back to the status code for unknown backend codes but keeps the message", () => {
    const err = apiErrorFromResponse(
      { error: { code: "weird", message: "Custom" } },
      new Response(null, { status: 404 }),
    );
    expect(err.code).toBe("not_found");
    expect(err.message).toBe("Custom");
  });
});
