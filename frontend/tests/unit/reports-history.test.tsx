import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReportsHistory } from "@/app/reports/reports-history";
import { RUNS_STORAGE_KEY } from "@/lib/runs-history";

import { makeRun, RUN_ID } from "./fixtures";
import { renderWithQueryClient } from "./test-utils";

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

function storeRuns() {
  window.localStorage.setItem(
    RUNS_STORAGE_KEY,
    JSON.stringify([
      { id: RUN_ID, projectName: "pocket-notes", createdAt: "2026-11-24T00:00:00Z" },
    ]),
  );
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => vi.unstubAllGlobals());

describe("ReportsHistory", () => {
  it("shows the empty state when nothing is stored", async () => {
    renderWithQueryClient(<ReportsHistory />);
    await waitFor(() => expect(screen.getByText("No reports yet")).toBeVisible());
    expect(screen.getByRole("link", { name: "Run an audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
  });

  it("lists stored runs with their live status", async () => {
    storeRuns();
    stubFetch(async () => json(makeRun()));
    renderWithQueryClient(<ReportsHistory />);

    await waitFor(() => expect(screen.getByText("pocket-notes")).toBeVisible());
    expect(screen.getByText("Finished")).toBeVisible();
    expect(screen.getByText("Fix first")).toBeVisible();
    expect(
      screen.getByRole("link", { name: "View the Launch Report for pocket-notes" }),
    ).toHaveAttribute("href", `/reports/${RUN_ID}`);
  });

  it("links an active run to its progress page", async () => {
    storeRuns();
    stubFetch(async () => json(makeRun({ status: "running", progress: 60 })));
    renderWithQueryClient(<ReportsHistory />);

    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "Follow the audit for pocket-notes" }),
      ).toHaveAttribute("href", `/audits/${RUN_ID}`),
    );
    expect(screen.getByText(/60% complete/)).toBeVisible();
  });

  it("marks an unloadable run and lets it be removed", async () => {
    const user = userEvent.setup();
    storeRuns();
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Audit run not found." } }, 404),
    );
    renderWithQueryClient(<ReportsHistory />);

    await waitFor(() =>
      expect(screen.getByText(/This run could not be loaded/)).toBeVisible(),
    );
    await user.click(screen.getByRole("button", { name: "Remove from history" }));
    await waitFor(() => expect(screen.getByText("No reports yet")).toBeVisible());
    expect(window.localStorage.getItem(RUNS_STORAGE_KEY)).toBe("[]");
  });
});
