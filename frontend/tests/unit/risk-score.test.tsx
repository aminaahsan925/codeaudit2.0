import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RiskScore } from "@/components/risk-score";
import { formatRiskScore } from "@/lib/report";

describe("RiskScore", () => {
  it("renders the score with one decimal and an accessible scale", () => {
    render(<RiskScore score={7.4} />);
    expect(screen.getByText("7.4")).toBeInTheDocument();
    expect(screen.getByText("out of 10")).toBeInTheDocument();
  });

  it.each([
    [0, "0.0"],
    [10, "10.0"],
    [3.7, "3.7"],
    [4.26, "4.3"],
    [-2, "0.0"],
    [15, "10.0"],
  ])("formats %s as %s", (score, expected) => {
    render(<RiskScore score={score} />);
    expect(screen.getByText(expected)).toBeInTheDocument();
    expect(formatRiskScore(score)).toBe(expected);
  });

  it("shows the decorative gauge dial under the number", () => {
    render(<RiskScore score={5} />);
    const gauge = screen.getByTestId("risk-gauge");
    expect(gauge).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByTestId("risk-gauge-arc")).toHaveAttribute(
      "stroke-dasharray",
      "50 100",
    );
  });

  it("clamps the gauge for out-of-range scores", () => {
    render(<RiskScore score={99} />);
    expect(screen.getByTestId("risk-gauge-arc")).toHaveAttribute(
      "stroke-dasharray",
      "100 100",
    );
  });
});
