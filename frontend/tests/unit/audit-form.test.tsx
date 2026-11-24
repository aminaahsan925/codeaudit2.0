import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuditForm } from "@/components/audit-form";

import { makeRun, RUN_ID } from "./fixtures";
import { renderWithQueryClient } from "./test-utils";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
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

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockClear();
  window.localStorage.clear();
});

describe("AuditForm", () => {
  it("renders the fields and the no-account note", () => {
    renderWithQueryClient(<AuditForm />);
    expect(screen.getByLabelText("Project name")).toBeVisible();
    expect(screen.getByLabelText("GitHub repo URL")).toBeVisible();
    expect(screen.getByLabelText(/Zip upload/)).toBeVisible();
    expect(screen.getByLabelText("Live URL")).toBeVisible();
    expect(screen.getByLabelText("Journey test email")).toBeVisible();
    expect(screen.getByLabelText("Journey test password")).toBeVisible();
    expect(screen.getByLabelText("Domain verification token")).toBeVisible();
    expect(screen.getByText(/No account needed/)).toBeVisible();
  });

  it("renders the custom journey section with the default journey info", () => {
    renderWithQueryClient(<AuditForm />);
    expect(
      screen.getByRole("heading", { name: /Custom journey/ }),
    ).toBeVisible();
    expect(
      screen.getByText(
        "Default journey: sign up, log in, add to cart, check out.",
      ),
    ).toBeVisible();
  });

  it("shows validation errors and does not submit an empty form", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch(async () => json(makeRun(), 201));
    renderWithQueryClient(<AuditForm />);

    await user.click(screen.getByRole("button", { name: "Run audit" }));

    expect(screen.getByText("Enter a project name.")).toBeVisible();
    expect(
      screen.getByText("Add a GitHub repo URL or upload a zip file."),
    ).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("submits a repo run and navigates to the run page", async () => {
    const user = userEvent.setup();
    stubFetch(async () => json(makeRun({ status: "queued" }), 201));
    renderWithQueryClient(<AuditForm />);

    await user.type(screen.getByLabelText("Project name"), "pocket-notes");
    await user.type(
      screen.getByLabelText("GitHub repo URL"),
      "https://github.com/example/pocket-notes",
    );
    await user.click(screen.getByRole("button", { name: "Run audit" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith(`/audits/${RUN_ID}`));
  });

  it("submits a zip run with journey credentials", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch(async () => json(makeRun({ status: "queued" }), 201));
    renderWithQueryClient(<AuditForm />);

    await user.type(screen.getByLabelText("Project name"), "pocket-notes");
    const zip = new File(["fake"], "app.zip", { type: "application/zip" });
    await user.upload(screen.getByLabelText(/Zip upload/), zip);
    await user.type(screen.getByLabelText("Journey test email"), "tester@example.com");
    await user.type(screen.getByLabelText("Journey test password"), "hunter2");
    await user.click(screen.getByRole("button", { name: "Run audit" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith(`/audits/${RUN_ID}`));
    const body = await fetchMock.mock.calls[0]![0].text();
    expect(body).toContain('name="zip_file"');
    expect(body).toContain("tester@example.com");
  });

  it("shows the API error when the audit cannot start", async () => {
    const user = userEvent.setup();
    stubFetch(async () =>
      json(
        { error: { code: "bad_request", message: "Too many audits this hour." } },
        429,
      ),
    );
    renderWithQueryClient(<AuditForm />);

    await user.type(screen.getByLabelText("Project name"), "pocket-notes");
    await user.type(
      screen.getByLabelText("GitHub repo URL"),
      "https://github.com/example/pocket-notes",
    );
    await user.click(screen.getByRole("button", { name: "Run audit" }));

    await waitFor(() =>
      expect(
        screen.getByText(/The audit could not start: Too many audits this hour\./),
      ).toBeVisible(),
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("disables the submit button while the run is starting", async () => {
    const user = userEvent.setup();
    let release: (value: Response) => void = () => {};
    stubFetch(
      () =>
        new Promise<Response>((resolve) => {
          release = resolve;
        }),
    );
    renderWithQueryClient(<AuditForm />);

    await user.type(screen.getByLabelText("Project name"), "pocket-notes");
    await user.type(
      screen.getByLabelText("GitHub repo URL"),
      "https://github.com/example/pocket-notes",
    );
    await user.click(screen.getByRole("button", { name: "Run audit" }));

    expect(
      screen.getByRole("button", { name: "Starting audit…" }),
    ).toBeDisabled();
    release(json(makeRun({ status: "queued" }), 201));
    await waitFor(() => expect(push).toHaveBeenCalled());
  });
});
