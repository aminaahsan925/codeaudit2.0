import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SeverityBadge } from "@/components/severity-badge";
import { VerdictBadge } from "@/components/verdict-badge";
import {
  SEVERITIES,
  SEVERITY_LABEL,
  VERDICTS,
  VERDICT_LABEL,
} from "@/lib/report";

describe("SeverityBadge", () => {
  it.each(SEVERITIES)("renders a text label for %s", (severity) => {
    render(<SeverityBadge severity={severity} />);
    const label = screen.getByText(SEVERITY_LABEL[severity]);
    expect(label).toBeInTheDocument();
    expect(label).toHaveAttribute("data-severity", severity);
  });

  it("uses a distinct readable label per level", () => {
    expect(new Set(Object.values(SEVERITY_LABEL)).size).toBe(SEVERITIES.length);
  });

  it("hides the decorative mark from assistive tech", () => {
    const { container } = render(<SeverityBadge severity="high" />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(container).toHaveTextContent(/^High$/);
  });

  it("accepts a custom class name", () => {
    render(<SeverityBadge severity="low" className="extra" />);
    expect(screen.getByText("Low")).toHaveClass("extra");
  });
});

describe("VerdictBadge", () => {
  it.each(VERDICTS)("renders a text label for %s", (verdict) => {
    render(<VerdictBadge verdict={verdict} />);
    const label = screen.getByText(VERDICT_LABEL[verdict]);
    expect(label).toBeInTheDocument();
    expect(label).toHaveAttribute("data-verdict", verdict);
  });

  it("has the expected labels", () => {
    expect(VERDICT_LABEL).toEqual({
      launch: "Launch",
      fix_first: "Fix first",
      do_not_launch: "Do not launch",
    });
  });

  it("hides the icon from assistive tech so the text is the name", () => {
    const { container } = render(<VerdictBadge verdict="do_not_launch" />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(container).toHaveTextContent(/^Do not launch$/);
  });

  it.each(["sm", "md", "lg"] as const)("renders at size %s", (size) => {
    render(<VerdictBadge verdict="launch" size={size} />);
    expect(screen.getByText("Launch")).toBeInTheDocument();
  });
});
