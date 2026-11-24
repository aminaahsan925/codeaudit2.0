import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FindingCard } from "@/components/finding-card";
import { ReportView } from "@/components/report-view";

import { makeFinding, makeReport, RUN_ID } from "./fixtures";
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

const FINDING_ID = "33333333-3333-4333-8333-333333333333";

describe("FindingCard tracking controls (signed-in report)", () => {
  it("shows an assignee input and a status dropdown with the current values", () => {
    renderWithQueryClient(
      <FindingCard
        finding={makeFinding({
          assignee: "amina@example.com",
          tracking_status: "in_progress",
        })}
        index={1}
        runId={RUN_ID}
      />,
    );

    const input = screen.getByLabelText("Assigned to") as HTMLInputElement;
    expect(input.value).toBe("amina@example.com");
    const select = screen.getByLabelText("Status") as HTMLSelectElement;
    expect(select.value).toBe("in_progress");
    expect(screen.getByRole("option", { name: "Open" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "In progress" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Fixed" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Ignored" })).toBeInTheDocument();
  });

  it("PATCHes the tracking status when the dropdown changes", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch(async () =>
      json(makeFinding({ tracking_status: "fixed" })),
    );
    renderWithQueryClient(
      <FindingCard finding={makeFinding()} index={1} runId={RUN_ID} />,
    );

    await user.selectOptions(screen.getByLabelText("Status"), "fixed");

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe(
      `/api/runs/${RUN_ID}/findings/${FINDING_ID}`,
    );
    expect(req.method).toBe("PATCH");
    expect(await req.json()).toEqual({ tracking_status: "fixed" });
  });

  it("PATCHes the assignee on blur", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch(async () =>
      json(makeFinding({ assignee: "hadi@example.com" })),
    );
    renderWithQueryClient(
      <FindingCard finding={makeFinding()} index={1} runId={RUN_ID} />,
    );

    const input = screen.getByLabelText("Assigned to");
    await user.click(input);
    await user.type(input, "hadi@example.com");
    await user.tab();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const req = fetchMock.mock.calls[0]![0];
    expect(req.method).toBe("PATCH");
    expect(await req.json()).toEqual({ assignee: "hadi@example.com" });
  });

  it("does not PATCH when the assignee did not change", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch(async () => json(makeFinding()));
    renderWithQueryClient(
      <FindingCard
        finding={makeFinding({ assignee: "amina@example.com" })}
        index={1}
        runId={RUN_ID}
      />,
    );

    await user.click(screen.getByLabelText("Assigned to"));
    await user.tab();

    // Give any stray save time to fire, then assert nothing went out.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows an error when saving fails", async () => {
    const user = userEvent.setup();
    stubFetch(async () =>
      json(
        { error: { code: "bad_request", message: "Assignee is too long." } },
        400,
      ),
    );
    renderWithQueryClient(
      <FindingCard finding={makeFinding()} index={1} runId={RUN_ID} />,
    );

    await user.selectOptions(screen.getByLabelText("Status"), "ignored");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Assignee is too long.",
    );
  });
});

describe("FindingCard tracking controls (shared report, read-only)", () => {
  it("shows assignment and status as text, with no controls", () => {
    renderWithQueryClient(
      <FindingCard
        finding={makeFinding({
          assignee: "amina@example.com",
          tracking_status: "in_progress",
        })}
        index={1}
        runId={RUN_ID}
        readOnly
      />,
    );

    expect(
      screen.getByText("Assigned to amina@example.com · In progress"),
    ).toBeVisible();
    expect(screen.queryByLabelText("Assigned to")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Status")).not.toBeInTheDocument();
  });

  it("shows Unassigned for an unassigned finding", () => {
    renderWithQueryClient(
      <FindingCard finding={makeFinding()} index={1} runId={RUN_ID} readOnly />,
    );

    expect(screen.getByText("Unassigned · Open")).toBeVisible();
  });
});

describe("ReportView readOnly plumbing", () => {
  it("offers editing by default and hides it when readOnly", () => {
    const { rerender } = renderWithQueryClient(
      <ReportView report={makeReport()} />,
    );
    expect(screen.getByLabelText("Assigned to")).toBeInTheDocument();
    expect(screen.getByLabelText("Status")).toBeInTheDocument();

    rerender(<ReportView report={makeReport()} readOnly />);
    expect(screen.queryByLabelText("Assigned to")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Status")).not.toBeInTheDocument();
    expect(screen.getByText("Unassigned · Open")).toBeVisible();
  });
});
