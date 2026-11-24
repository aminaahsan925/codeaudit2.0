import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, updateFinding } from "@/lib/api";

import { makeFinding, RUN_ID } from "./fixtures";

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

const FINDING_ID = "33333333-3333-4333-8333-333333333333";

describe("updateFinding", () => {
  it("PATCHes the finding with the given assignment", async () => {
    const fetchMock = stubFetch(async () =>
      json(makeFinding({ assignee: "amina@example.com", tracking_status: "fixed" })),
    );
    const updated = await updateFinding(RUN_ID, FINDING_ID, {
      assignee: "amina@example.com",
      tracking_status: "fixed",
    });
    expect(updated.assignee).toBe("amina@example.com");
    expect(updated.tracking_status).toBe("fixed");
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe(
      `/api/runs/${RUN_ID}/findings/${FINDING_ID}`,
    );
    expect(req.method).toBe("PATCH");
    expect(await req.json()).toEqual({
      assignee: "amina@example.com",
      tracking_status: "fixed",
    });
  });

  it("maps a 400 to bad_request", async () => {
    stubFetch(async () =>
      json(
        {
          error: {
            code: "bad_request",
            message: "tracking_status must be one of: open, in_progress, fixed, ignored.",
          },
        },
        400,
      ),
    );
    const err = await catchError(
      updateFinding(RUN_ID, FINDING_ID, { tracking_status: "done" }),
    );
    expect(err.code).toBe("bad_request");
    expect(err.status).toBe(400);
  });

  it("maps an unknown finding to not_found", async () => {
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Finding not found." } }, 404),
    );
    const err = await catchError(
      updateFinding(RUN_ID, FINDING_ID, { tracking_status: "fixed" }),
    );
    expect(err.code).toBe("not_found");
  });
});
