import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AUTO_OPEN_DELAY_MS, RunPageContent } from "@/app/(app)/audits/[id]/run-page-content";
import { getStages } from "@/app/(app)/audits/[id]/run-stages";

import { makeRun, RUN_ID } from "./fixtures";
import { renderWithQueryClient } from "./test-utils";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));

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

/** The pipeline row for a stage label, and the state word it shows. */
function stageRow(label: string) {
  const list = screen.getByRole("list", { name: "Audit stages" });
  const row = within(list).getByText(label).closest("li");
  if (!row) throw new Error(`No stage row for ${label}`);
  return row;
}

beforeEach(() => {
  router.push.mockReset();
  router.replace.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("getStages", () => {
  it("maps the runner's progress values to stages", () => {
    const states = (progress: number) =>
      getStages({ status: "running", progress, live_url: "https://x.app" }).map((s) => s.state);
    expect(states(5)).toEqual(["running", "pending", "pending", "pending", "pending", "pending"]);
    expect(states(40)).toEqual(["done", "done", "running", "pending", "pending", "pending"]);
    expect(states(90)).toEqual(["done", "done", "done", "done", "done", "running"]);
  });

  it("skips the live stages without a live URL", () => {
    const stages = getStages({ status: "running", progress: 60, live_url: null });
    expect(stages.map((s) => s.state)).toEqual([
      "done",
      "done",
      "skipped",
      "skipped",
      "running",
      "pending",
    ]);
  });

  it("blames the stage that held the progress when a run fails", () => {
    const stages = getStages({ status: "failed", progress: 15, live_url: "https://x.app" });
    expect(stages.map((s) => s.state)).toEqual([
      "done",
      "failed",
      "not_run",
      "not_run",
      "not_run",
      "not_run",
    ]);
    expect(
      getStages({ status: "failed", progress: 0, live_url: null }).some((s) => s.state === "failed"),
    ).toBe(false);
  });
});

describe("RunPageContent", () => {
  it("shows a pipeline with the running stage and the progress percent", async () => {
    stubFetch(async () =>
      json(
        makeRun({
          status: "running",
          progress: 45,
          started_at: new Date().toISOString(),
          finished_at: null,
          verdict: null,
          risk_score: null,
        }),
      ),
    );
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByRole("heading", { level: 1, name: "pocket-notes" })).toBeVisible(),
    );
    expect(screen.getAllByText("Running").length).toBeGreaterThan(0);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "45");
    expect(screen.getByText(/This page updates on its own/)).toBeVisible();
    expect(screen.getByText(/Running for \d+ s/)).toBeVisible();

    expect(stageRow("Get the code")).toHaveTextContent("Done");
    expect(stageRow("Scan the code")).toHaveTextContent("Done");
    expect(stageRow("Check the live site")).toHaveTextContent("Running");
    expect(stageRow("Walk the login journey")).toHaveTextContent("Waiting");
    expect(screen.queryByText("Taking longer than usual")).not.toBeInTheDocument();
    // No severity counts on the run, so none are shown.
    expect(screen.queryByText(/Critical|High|Medium|Low/)).not.toBeInTheDocument();
  });

  it("says when a run is taking longer than usual and what is still running", async () => {
    stubFetch(async () =>
      json(
        makeRun({
          status: "running",
          progress: 15,
          started_at: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
          finished_at: null,
          verdict: null,
          risk_score: null,
        }),
      ),
    );
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    const notice = await screen.findByRole("region", { name: "Taking longer than usual" });
    expect(notice).toHaveTextContent("Still running: Scan the code.");
  });

  it("reveals the verdict, then opens the report on its own", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    stubFetch(async () => json(makeRun({ status: "succeeded" })));
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    await waitFor(() => expect(screen.getByText("Audit complete")).toBeVisible());
    // The verdict pops in through motion, which jsdom never runs, so check presence.
    expect(screen.getByText("Fix first")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open the report" })).toHaveAttribute(
      "href",
      `/reports/${RUN_ID}`,
    );
    expect(screen.getByText(/Opening the report/)).toBeVisible();
    expect(stageRow("Write the report")).toHaveTextContent("Done");

    act(() => {
      vi.advanceTimersByTime(AUTO_OPEN_DELAY_MS + 50);
    });
    expect(router.replace).toHaveBeenCalledWith(`/reports/${RUN_ID}`);
  });

  it("stays on the page when the person presses a key first", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    stubFetch(async () => json(makeRun({ status: "succeeded" })));
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    await waitFor(() => expect(screen.getByText("Audit complete")).toBeVisible());
    fireEvent.keyDown(document.body, { key: "Tab" });
    act(() => {
      vi.advanceTimersByTime(AUTO_OPEN_DELAY_MS * 2);
    });
    expect(router.replace).not.toHaveBeenCalled();
    expect(screen.queryByText(/Opening the report/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open the report" })).toBeVisible();
  });

  it("names the failed stage and shows the error with two ways forward", async () => {
    stubFetch(async () =>
      json(
        makeRun({
          status: "failed",
          progress: 5,
          error: "Could not clone the repo: repository not found.",
          verdict: null,
          risk_score: null,
        }),
      ),
    );
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("This audit failed")).toBeVisible();
    expect(alert).toHaveTextContent("It stopped at Get the code.");
    expect(
      within(alert).getByText("Could not clone the repo: repository not found."),
    ).toBeVisible();
    expect(within(alert).getByRole("link", { name: "Try again" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
    expect(within(alert).getByRole("link", { name: "Edit the audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
    expect(stageRow("Get the code")).toHaveTextContent("Failed");
    expect(stageRow("Scan the code")).toHaveTextContent("Not run");
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("shows a not-found state for an unknown run", async () => {
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Audit run not found." } }, 404),
    );
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByText("This audit run was not found")).toBeVisible(),
    );
  });

  it("shows a retryable error when the API fails", async () => {
    stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    });
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByText("The run could not be loaded")).toBeVisible(),
    );
    expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
  });
});
