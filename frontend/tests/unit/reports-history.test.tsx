import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReportsHistory } from "@/app/(app)/reports/reports-history";
import { formatDateTime } from "@/lib/dates";
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
    expect(screen.getByRole("link", { name: "See an example report" })).toHaveAttribute(
      "href",
      "/#example",
    );
  });

  it("shows the stored name with skeleton cells while a run loads", async () => {
    storeRuns();
    stubFetch(() => new Promise<Response>(() => {}));
    renderWithQueryClient(<ReportsHistory />);

    const list = await screen.findByRole("list", { name: "Reports" });
    const row = within(list).getByRole("listitem");
    expect(row).toHaveTextContent("pocket-notes, loading");
    expect(row.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
    expect(within(list).queryByRole("link")).not.toBeInTheDocument();
  });

  it("lists stored runs with their live status", async () => {
    storeRuns();
    stubFetch(async () => json(makeRun()));
    renderWithQueryClient(<ReportsHistory />);

    const link = await screen.findByRole("link", {
      name: "View the Launch Report for pocket-notes",
    });
    expect(screen.getByText("Finished")).toBeVisible();
    expect(screen.getByText("Fix first")).toBeVisible();
    expect(screen.getByText("4.3")).toBeVisible();
    expect(link).toHaveAttribute("href", `/reports/${RUN_ID}`);
    // The whole row is the link: name, verdict, score, date and status sit inside it.
    const date = formatDateTime("2026-11-24T00:00:00Z");
    for (const text of ["pocket-notes", "Fix first", "4.3", date ?? "", "Finished"]) {
      expect(within(link).getByText(text)).toBeVisible();
    }
    expect(link).toHaveAccessibleDescription(
      `Finished. Verdict Fix first. Risk score 4.3 out of 10. ${date}.`,
    );
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
