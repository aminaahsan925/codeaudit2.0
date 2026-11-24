import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SampleFindings } from "@/components/sample-findings";
import { SAMPLE_FINDINGS } from "@/lib/sample-report";

function findingButton(name: RegExp) {
  return screen.getByRole("button", { name });
}

describe("SampleFindings", () => {
  it("lists every sample finding as a disclosure button", () => {
    render(<SampleFindings />);

    expect(screen.getAllByRole("button")).toHaveLength(SAMPLE_FINDINGS.length);
    for (const finding of SAMPLE_FINDINGS) {
      expect(
        screen.getByRole("button", { name: new RegExp(finding.title) }),
      ).toHaveAttribute("aria-controls");
    }
  });

  it("opens the first finding by default and shows its source proof with the flagged line", () => {
    render(<SampleFindings />);

    expect(findingButton(/admin key/)).toHaveAttribute("aria-expanded", "true");
    const source = screen.getByRole("region", { name: "Source excerpt from src/lib/db.ts" });
    expect(within(source).getByText(/const adminKey/)).toBeInTheDocument();
    expect(within(source).getByText("(flagged)")).toBeInTheDocument();
    expect(screen.getByText("How the key reaches the browser")).toBeInTheDocument();
  });

  it("keeps closed panels out of the accessibility tree", () => {
    render(<SampleFindings />);

    const closed = findingButton(/other users’ notes/);
    expect(closed).toHaveAttribute("aria-expanded", "false");
    const panel = document.getElementById(closed.getAttribute("aria-controls") ?? "");
    // Browsers drop inert content from the accessibility tree and tab order;
    // jsdom does not implement that, so assert the attribute itself.
    expect(panel).toHaveAttribute("inert");
  });

  it("opens one finding at a time and shows the live request proof", async () => {
    const user = userEvent.setup();
    render(<SampleFindings />);

    await user.click(findingButton(/other users’ notes/));

    expect(findingButton(/other users’ notes/)).toHaveAttribute("aria-expanded", "true");
    expect(findingButton(/admin key/)).toHaveAttribute("aria-expanded", "false");
    const response = screen.getByRole("region", { name: "Response received" });
    expect(within(response).getByText(/"owner": "test-user-a"/)).toBeInTheDocument();
    expect(screen.getByText(/User B should get 403 or 404/)).toBeInTheDocument();
  });

  it("closes an open finding when it is clicked again", async () => {
    const user = userEvent.setup();
    render(<SampleFindings />);

    await user.click(findingButton(/admin key/));

    for (const button of screen.getAllByRole("button")) {
      expect(button).toHaveAttribute("aria-expanded", "false");
    }
  });

  it("shows the missing header as the flagged line for the CSP finding", async () => {
    const user = userEvent.setup();
    render(<SampleFindings />);

    await user.click(findingButton(/Content-Security-Policy/));

    const headers = screen.getByRole("region", { name: "Response headers" });
    expect(within(headers).getByText("content-security-policy: (missing)")).toBeInTheDocument();
    expect(within(headers).getByText("(flagged)")).toBeInTheDocument();
  });
});
