import { screen, waitFor } from "@testing-library/react";
import { LazyMotion, MotionConfig, MotionGlobalConfig, domAnimation } from "motion/react";
import type { ReactElement } from "react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { SharedReportPage } from "@/app/(shared)/r/[token]/shared-report-page";
import { ReportPage } from "@/app/(app)/reports/[id]/report-page";

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

// The report animates in; render under the app's motion providers with
// animations jumping to their end state.
beforeAll(() => {
  MotionGlobalConfig.skipAnimations = true;
});

function renderPage(ui: ReactElement) {
  return renderWithQueryClient(
    <LazyMotion features={domAnimation} strict>
      <MotionConfig reducedMotion="user">{ui}</MotionConfig>
    </LazyMotion>,
  );
}

describe("ReportPage", () => {
  it("renders the report for a finished run", async () => {
    stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === `/api/runs/${RUN_ID}`) return json(makeRun());
      if (path === `/api/reports/shared/${SHARE_TOKEN}`) return json(makeReport());
      return json({ error: { code: "not_found", message: "Nope." } }, 404);
    });
    renderPage(<ReportPage runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByText("Database admin key is shipped to the browser")).toBeVisible(),
    );
    await waitFor(() => expect(screen.getByText("Fix first")).toBeVisible());
    expect(screen.getByRole("button", { name: "Rerun audit" })).toBeVisible();
    expect(screen.queryByText("Shared report, read only")).not.toBeInTheDocument();
  });

  it("shows a loading skeleton while the report loads", () => {
    stubFetch(() => new Promise<Response>(() => {}));
    renderPage(<ReportPage runId={RUN_ID} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading the report.");
  });

  it("shows an error with a retry when the report fails to load", async () => {
    stubFetch(async () =>
      json({ error: { code: "internal_error", message: "Something broke." } }, 500),
    );
    renderPage(<ReportPage runId={RUN_ID} />);
    await waitFor(
      () => expect(screen.getByText("The report could not be loaded")).toBeVisible(),
      { timeout: 5000 },
    );
    expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
    expect(screen.getByRole("link", { name: "See your reports" })).toHaveAttribute(
      "href",
      "/reports",
    );
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
    renderPage(<ReportPage runId={RUN_ID} />);

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
    renderPage(<ReportPage runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByText("This report was not found")).toBeVisible(),
    );
    expect(screen.getByRole("link", { name: "Run an audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
  });
});

describe("SharedReportPage", () => {
  it("renders the report by token, read only", async () => {
    stubFetch(async () => json(makeReport()));
    renderPage(<SharedReportPage token={SHARE_TOKEN} />);

    await waitFor(() =>
      expect(screen.getByText("Database admin key is shipped to the browser")).toBeVisible(),
    );
    expect(screen.getByText("Shared report, read only")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Rerun audit" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Run your own audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
  });

  it("shows a not-found state for an unknown token", async () => {
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Report not found." } }, 404),
    );
    renderPage(<SharedReportPage token="bad-token" />);

    await waitFor(() =>
      expect(screen.getByText("This report was not found")).toBeVisible(),
    );
  });
});
