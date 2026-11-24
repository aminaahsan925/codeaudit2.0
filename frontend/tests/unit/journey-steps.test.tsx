import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JourneySteps } from "@/components/journey-steps";

import { RUN_ID } from "./fixtures";

describe("JourneySteps", () => {
  it("renders nothing without steps", () => {
    const { container } = render(<JourneySteps steps={[]} runId={RUN_ID} />);
    expect(container).toBeEmptyDOMElement();
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
  });

  it("draws a timeline rail with a connector between steps, none after the last", () => {
    const { container } = render(
      <JourneySteps
        runId={RUN_ID}
        steps={[
          { name: "Sign up", status: "passed", screenshot_url: null, error: null },
          { name: "Log in", status: "passed", screenshot_url: null, error: null },
          { name: "Check out", status: "failed", screenshot_url: null, error: null },
        ]}
      />,
    );
    expect(container.querySelectorAll("li > div > span.w-0\\.5")).toHaveLength(2);
  });
});
