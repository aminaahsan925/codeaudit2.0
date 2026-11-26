import { screen, waitFor, within } from "@testing-library/react";
import userEvent, { type UserEvent } from "@testing-library/user-event";
import { LazyMotion, MotionGlobalConfig, domAnimation } from "motion/react";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

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

function renderForm() {
  return renderWithQueryClient(
    <LazyMotion features={domAnimation}>
      <AuditForm />
    </LazyMotion>,
  );
}

function stepHeading(name: RegExp) {
  return screen.getByRole("heading", { level: 2, name });
}

/** Fills the Code step with a repo and skips the optional steps. */
async function reachReviewWithRepo(user: UserEvent) {
  await user.type(screen.getByLabelText("Project name"), "pocket-notes");
  await user.type(
    screen.getByLabelText("GitHub repo URL"),
    "https://github.com/example/pocket-notes",
  );
  await user.click(screen.getByRole("button", { name: "Next" }));
  await user.click(screen.getByRole("button", { name: "Skip this step" }));
  await user.click(screen.getByRole("button", { name: "Skip this step" }));
  await waitFor(() => expect(stepHeading(/Review and run/)).toBeVisible());
}

beforeAll(() => {
  // Step changes animate; finish them instantly so content is visible at once.
  MotionGlobalConfig.skipAnimations = true;
});

afterAll(() => {
  MotionGlobalConfig.skipAnimations = false;
});

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockClear();
  window.localStorage.clear();
});

describe("AuditForm", () => {
  it("starts on the Code step with the stepper and the no-account note later", () => {
    renderForm();
    const steps = screen.getByRole("list", { name: "Audit steps" });
    const items = within(steps).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "1CodeCurrent step",
      "2Live siteOptional",
      "3Test loginOptional",
      "4ReviewLast step",
    ]);
    expect(within(steps).getByText("Code").closest("[aria-current]")).toHaveAttribute(
      "aria-current",
      "step",
    );
    expect(stepHeading(/Your code/)).toBeVisible();
    expect(screen.getByLabelText("Project name")).toBeVisible();
    expect(screen.getByLabelText("GitHub repo URL")).toBeVisible();
    expect(screen.getByRole("radio", { name: "GitHub URL" })).toBeChecked();
    expect(screen.queryByLabelText(/Zip upload/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Skip this step" })).not.toBeInTheDocument();
  });

  it("shows one code input at a time", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("radio", { name: "Zip file" }));

    expect(screen.getByLabelText(/Zip upload/)).toBeVisible();
    expect(screen.queryByLabelText("GitHub repo URL")).not.toBeInTheDocument();
  });

  it("shows validation errors on Next and does not advance or submit an empty form", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch(async () => json(makeRun(), 201));
    renderForm();

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Enter a project name.")).toBeVisible();
    expect(
      screen.getByText("Add a GitHub repo URL or upload a zip file."),
    ).toBeVisible();
    expect(stepHeading(/Your code/)).toBeVisible();
    expect(screen.getByLabelText("Project name")).toHaveFocus();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("validates a field when it loses focus, not while typing, and links the error", async () => {
    const user = userEvent.setup();
    renderForm();
    const repo = screen.getByLabelText("GitHub repo URL");

    await user.type(repo, "http://gitlab.com/x");
    expect(screen.queryByText(/Enter an https GitHub URL/)).not.toBeInTheDocument();
    expect(repo).toHaveAttribute("aria-invalid", "false");

    await user.tab();

    const error = screen.getByText(/Enter an https GitHub URL/);
    expect(error).toBeVisible();
    expect(repo).toHaveAttribute("aria-invalid", "true");
    expect(repo.getAttribute("aria-describedby")).toContain(error.id);

    // Fixing the value clears the error while typing.
    await user.clear(repo);
    await user.type(repo, "https://github.com/example/pocket-notes");
    expect(screen.queryByText(/Enter an https GitHub URL/)).not.toBeInTheDocument();
  });

  it("moves through the steps and focuses each step heading", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Project name"), "pocket-notes");
    await user.type(
      screen.getByLabelText("GitHub repo URL"),
      "https://github.com/example/pocket-notes",
    );
    await user.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => expect(stepHeading(/Your live site/)).toHaveFocus());
    expect(screen.getByLabelText("Live site URL")).toBeVisible();
    expect(screen.getByLabelText("Domain verification token")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "What is Domain verification?" }),
    ).toBeVisible();
    const steps = screen.getByRole("list", { name: "Audit steps" });
    expect(within(steps).getByRole("button", { name: /Code\s*Done/ })).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Back" }));
    await waitFor(() => expect(stepHeading(/Your code/)).toHaveFocus());
    expect(screen.getByLabelText("Project name")).toHaveValue("pocket-notes");
  });

  it("shows the domain verification tag with the token and a copy button", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Project name"), "pocket-notes");
    await user.type(
      screen.getByLabelText("GitHub repo URL"),
      "https://github.com/example/pocket-notes",
    );
    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByRole("button", { name: /Copy tag/ })).toBeDisabled();
    await user.type(screen.getByLabelText("Live site URL"), "https://app.example.com");
    await user.type(screen.getByLabelText("Domain verification token"), "abc123");

    expect(
      screen.getByText('<meta name="launchaudit-verification" content="abc123">'),
    ).toBeVisible();
    expect(
      screen.getByText("https://app.example.com/.well-known/launchaudit-verification.txt"),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: /Copy tag/ })).toBeEnabled();
  });

  it("summarises the run on Review", async () => {
    const user = userEvent.setup();
    renderForm();

    await reachReviewWithRepo(user);

    expect(screen.getByText("https://github.com/example/pocket-notes")).toBeVisible();
    expect(screen.getByText("Skipped. Only the code is checked.")).toBeVisible();
    expect(screen.getByText(/No account needed/)).toBeVisible();
    const steps = screen.getByRole("list", { name: "Audit steps" });
    expect(within(steps).getByRole("button", { name: /Live site\s*Skipped/ })).toBeVisible();
  });

  it("submits a repo run and navigates to the run page", async () => {
    const user = userEvent.setup();
    stubFetch(async () => json(makeRun({ status: "queued" }), 201));
    renderForm();

    await reachReviewWithRepo(user);
    await user.click(screen.getByRole("button", { name: "Run audit" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith(`/audits/${RUN_ID}`));
  });

  it("submits a zip run with journey credentials", async () => {
    const user = userEvent.setup();
    const fetchMock = stubFetch(async () => json(makeRun({ status: "queued" }), 201));
    renderForm();

    await user.type(screen.getByLabelText("Project name"), "pocket-notes");
    await user.click(screen.getByRole("radio", { name: "Zip file" }));
    const zip = new File(["fake"], "app.zip", { type: "application/zip" });
    await user.upload(screen.getByLabelText(/Zip upload/), zip);
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("button", { name: "Skip this step" }));
    await user.type(screen.getByLabelText("Test account email"), "tester@example.com");
    await user.type(screen.getByLabelText("Test account password"), "hunter2");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("button", { name: "Run audit" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith(`/audits/${RUN_ID}`));
    const body = await fetchMock.mock.calls[0]![0].text();
    expect(body).toContain('name="zip_file"');
    expect(body).toContain("tester@example.com");
  });

  it("asks for both test login fields before moving on", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Project name"), "pocket-notes");
    await user.type(
      screen.getByLabelText("GitHub repo URL"),
      "https://github.com/example/pocket-notes",
    );
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("button", { name: "Skip this step" }));
    await user.type(screen.getByLabelText("Test account email"), "tester@example.com");
    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(
      screen.getByText("Provide both a journey email and password, or neither."),
    ).toBeVisible();
    expect(stepHeading(/Test login/)).toBeVisible();
  });

  it("shows the API error when the audit cannot start", async () => {
    const user = userEvent.setup();
    stubFetch(async () =>
      json(
        { error: { code: "bad_request", message: "Too many audits this hour." } },
        429,
      ),
    );
    renderForm();

    await reachReviewWithRepo(user);
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
    renderForm();

    await reachReviewWithRepo(user);
    await user.click(screen.getByRole("button", { name: "Run audit" }));

    expect(
      screen.getByRole("button", { name: "Starting audit…" }),
    ).toBeDisabled();
    release(json(makeRun({ status: "queued" }), 201));
    await waitFor(() => expect(push).toHaveBeenCalled());
  });
});
