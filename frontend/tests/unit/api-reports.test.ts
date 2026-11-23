import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  getReport,
  getSharedReport,
  reportPdfUrl,
  sharedReportPath,
} from "@/lib/api";

import { makeReport, RUN_ID, SHARE_TOKEN } from "./fixtures";

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

describe("getReport", () => {
  it("fetches the report for a run id", async () => {
    const fetchMock = stubFetch(async () => json(makeReport()));
    const report = await getReport(RUN_ID);
    expect(report.run.id).toBe(RUN_ID);
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe(`/api/runs/${RUN_ID}/report`);
    expect(req.method).toBe("GET");
  });

  it("maps a 401 to unauthorized", async () => {
    stubFetch(async () =>
      json(
        { error: { code: "unauthorized", message: "Missing or invalid bearer token." } },
        401,
      ),
    );
    const err = await catchError(getReport(RUN_ID));
    expect(err.code).toBe("unauthorized");
    expect(err.status).toBe(401);
  });
});

describe("getSharedReport", () => {
  it("fetches the report by share token", async () => {
    const fetchMock = stubFetch(async () => json(makeReport()));
    const report = await getSharedReport(SHARE_TOKEN);
    expect(report.findings).toHaveLength(1);
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe(`/api/reports/shared/${SHARE_TOKEN}`);
    expect(req.method).toBe("GET");
  });

  it("maps an unknown token to not_found", async () => {
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Report not found." } }, 404),
    );
    const err = await catchError(getSharedReport("nope"));
    expect(err.code).toBe("not_found");
  });
});

describe("sharedReportPath", () => {
  it("builds the /r/[token] route", () => {
    expect(sharedReportPath("abc-123")).toBe("/r/abc-123");
  });
});

describe("reportPdfUrl", () => {
  it("builds the PDF link with the share token as the query", () => {
    expect(reportPdfUrl(RUN_ID, SHARE_TOKEN)).toBe(
      `http://localhost:8000/api/runs/${RUN_ID}/report.pdf?token=${SHARE_TOKEN}`,
    );
  });

  it("returns null without a share token", () => {
    expect(reportPdfUrl(RUN_ID, null)).toBeNull();
  });
});
