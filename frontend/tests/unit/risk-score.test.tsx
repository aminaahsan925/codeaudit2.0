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

  it("hides the decorative gauge from assistive tech and fills proportionally", () => {
    const { container } = render(<RiskScore score={5} />);
    const gauge = container.querySelector('[aria-hidden="true"].w-full');
    expect(gauge).not.toBeNull();
    const fill = gauge!.querySelector<HTMLElement>(".absolute");
    expect(fill!.style.width).toBe("50%");
  });

  it("clamps the gauge fill for out-of-range scores", () => {
    const { container } = render(<RiskScore score={99} />);
    const fill = container.querySelector<HTMLElement>(
      '[aria-hidden="true"].w-full .absolute',
    );
    expect(fill!.style.width).toBe("100%");
  });
});
