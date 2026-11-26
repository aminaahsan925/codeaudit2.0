import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RunPageContent } from "@/app/audits/[id]/run-page-content";

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

afterEach(() => vi.unstubAllGlobals());

describe("RunPageContent", () => {
  it("shows progress while the run is active", async () => {
    stubFetch(async () => json(makeRun({ status: "running", progress: 45 })));
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    await waitFor(() =>
      expect(screen.getByText("Audit: pocket-notes")).toBeVisible(),
    );
    expect(screen.getByText("Running")).toBeVisible();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "45");
    expect(screen.getByText(/This page updates on its own/)).toBeVisible();
  });

  it("links to the report when the run succeeds", async () => {
    stubFetch(async () => json(makeRun({ status: "succeeded" })));
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    await waitFor(() => expect(screen.getByText("Audit complete")).toBeVisible());
    expect(screen.getByRole("link", { name: "View the Launch Report" })).toHaveAttribute(
      "href",
      `/reports/${RUN_ID}`,
    );
  });

  it("shows the run's error message when it fails", async () => {
    stubFetch(async () =>
      json(
        makeRun({
          status: "failed",
          error: "Could not clone the repo: repository not found.",
        }),
      ),
    );
    renderWithQueryClient(<RunPageContent runId={RUN_ID} />);

    await waitFor(() => expect(screen.getByText("This audit failed")).toBeVisible());
    expect(
      screen.getByText("Could not clone the repo: repository not found."),
    ).toBeVisible();
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
