import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JourneySteps } from "@/components/journey-steps";

import { RUN_ID } from "./fixtures";

describe("JourneySteps", () => {
  it("explains how to get screenshots when a code-only run has no steps", () => {
    render(<JourneySteps steps={[]} runId={RUN_ID} />);
    expect(
      screen.getByRole("heading", { level: 2, name: "Journey through the live app" }),
    ).toBeVisible();
    expect(screen.getByText("No screenshots for this audit")).toBeVisible();
    expect(screen.getByText(/This audit checked the code only/)).toBeVisible();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("points at the journey login when the live site was checked without steps", () => {
    render(<JourneySteps steps={[]} runId={RUN_ID} liveUrl="https://app.example.com" />);
    expect(screen.getByText(/checked the live site but did not walk through it/)).toBeVisible();
  });

  it("renders each step with its status, error and screenshot", () => {
    render(
      <JourneySteps
        runId={RUN_ID}
        steps={[
          { name: "Sign up", status: "passed", screenshot_url: "signup.png", error: null },
          {
            name: "Check out",
            status: "failed",
            screenshot_url: "checkout.png",
            error: "Payment failed: the checkout returned HTTP 500.",
          },
          { name: "Log in", status: "skipped", screenshot_url: null, error: null },
        ]}
      />,
    );

    expect(screen.getByText("Journey through the live app")).toBeVisible();
    expect(screen.getByText(/1\. Sign up/)).toBeVisible();
    expect(screen.getByText(/2\. Check out/)).toBeVisible();
    expect(screen.getByText("Payment failed: the checkout returned HTTP 500.")).toBeVisible();
    expect(screen.getByAltText("Screenshot of the Sign up step")).toHaveAttribute(
      "src",
      `http://localhost:8000/api/runs/${RUN_ID}/artifacts/signup.png`,
    );
    expect(screen.queryByAltText("Screenshot of the Log in step")).not.toBeInTheDocument();
    expect(screen.getByText("No screenshot")).toBeVisible();
    expect(screen.getByText("1 of 3 steps failed.", { exact: false })).toBeVisible();
  });
});
