import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SharedReportPage } from "@/app/r/[token]/shared-report-page";
import { ReportPage } from "@/app/reports/[id]/report-page";

import { makeReport, makeRun, RUN_ID, SHARE_TOKEN } from "./fixtures";
import { renderWithQueryClient } from "./test-utils";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

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

afterEach(() => vi.unstubAllGlobals());

describe("ReportPage", () => {
  it("renders the report for a finished run", async () => {
    stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === `/api/runs/${RUN_ID}`) return json(makeRun());
      if (path === `/api/reports/shared/${SHARE_TOKEN}`) return json(makeReport());
      return json({ error: { code: "not_found", message: "Nope." } }, 404);
    });
    renderWithQueryClient(<ReportPage runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByText("Database admin key is shipped to the browser")).toBeVisible(),
    );
    expect(screen.getByText("Fix first")).toBeVisible();
  });

  it("shows the still-running state instead of an empty report", async () => {
    const running = makeRun({ status: "running", progress: 30, verdict: null, risk_score: null });
    stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === `/api/runs/${RUN_ID}`) return json(running);
      if (path === `/api/reports/shared/${SHARE_TOKEN}`) {
        return json(makeReport({ run: running, findings: [] }));
      }
      return json({ error: { code: "not_found", message: "Nope." } }, 404);
    });
    renderWithQueryClient(<ReportPage runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByText(/This audit is still running/)).toBeVisible(),
    );
    expect(screen.getByRole("link", { name: "Follow the audit" })).toHaveAttribute(
      "href",
      `/audits/${RUN_ID}`,
    );
  });

  it("shows a not-found state for an unknown run", async () => {
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Audit run not found." } }, 404),
    );
    renderWithQueryClient(<ReportPage runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByText("This report was not found")).toBeVisible(),
    );
  });
});

describe("SharedReportPage", () => {
  it("renders the report by token", async () => {
    stubFetch(async () => json(makeReport()));
    renderWithQueryClient(<SharedReportPage token={SHARE_TOKEN} />);

    await waitFor(() =>
      expect(screen.getByText("Database admin key is shipped to the browser")).toBeVisible(),
    );
  });

  it("shows a not-found state for an unknown token", async () => {
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Report not found." } }, 404),
    );
    renderWithQueryClient(<SharedReportPage token="bad-token" />);

    await waitFor(() =>
      expect(screen.getByText("This report was not found")).toBeVisible(),
    );
  });
});
