import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  GlobeIcon,
  InjectionIcon,
  KeyIcon,
  LockIcon,
  PackageIcon,
  ShieldScriptIcon,
} from "@/components/graphics/check-icons";
import { HeroIllustration } from "@/components/graphics/hero-illustration";
import { RiskGauge, riskBand } from "@/components/graphics/risk-gauge";
import { SeverityBar } from "@/components/graphics/severity-bar";
import {
  CodeInIcon,
  ReportIcon,
  ScanIcon,
} from "@/components/graphics/step-icons";

describe("riskBand", () => {
  it.each([
    [0, "launch"],
    [2, "launch"],
    [2.1, "fix"],
    [5, "fix"],
    [5.1, "block"],
    [10, "block"],
  ] as const)("scores %s as %s", (score, band) => {
    expect(riskBand(score)).toBe(band);
  });
});

describe("RiskGauge", () => {
  it("renders a decorative gauge with an arc proportional to the score", () => {
    const { container } = render(<RiskGauge score={5} />);
    const gauge = screen.getByTestId("risk-gauge");
    expect(gauge).toHaveAttribute("aria-hidden", "true");
    const arc = screen.getByTestId("risk-gauge-arc");
    expect(arc).toHaveAttribute("stroke-dasharray", "50 100");
    expect(container.querySelectorAll("line")).toHaveLength(4);
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });

  it("colours the arc by verdict band", () => {
    const { rerender } = render(<RiskGauge score={1} />);
    expect(screen.getByTestId("risk-gauge-arc")).toHaveClass("stroke-verdict-launch");
    rerender(<RiskGauge score={4.3} />);
    expect(screen.getByTestId("risk-gauge-arc")).toHaveClass("stroke-verdict-fix");
    rerender(<RiskGauge score={8.3} />);
    expect(screen.getByTestId("risk-gauge-arc")).toHaveClass("stroke-verdict-block");
  });

  it("clamps out-of-range scores", () => {
    const { rerender } = render(<RiskGauge score={99} />);
    expect(screen.getByTestId("risk-gauge-arc")).toHaveAttribute(
      "stroke-dasharray",
      "100 100",
    );
    rerender(<RiskGauge score={-4} />);
    expect(screen.getByTestId("risk-gauge-arc")).toHaveAttribute(
      "stroke-dasharray",
      "0 100",
    );
  });
});

describe("SeverityBar", () => {
  it("renders segments sized by each severity's share", () => {
    render(
      <SeverityBar counts={{ critical: 1, high: 1, medium: 2, low: 0 }} />,
    );
    const bar = screen.getByTestId("severity-bar");
    expect(bar).toHaveAttribute("aria-hidden", "true");
    const critical = bar.querySelector<HTMLElement>('[data-severity="critical"]');
    const medium = bar.querySelector<HTMLElement>('[data-severity="medium"]');
    expect(critical!.style.width).toBe("25%");
    expect(medium!.style.width).toBe("50%");
    expect(bar.querySelector('[data-severity="low"]')).toBeNull();
  });

  it("renders an empty track when there are no findings", () => {
    render(<SeverityBar counts={{ critical: 0, high: 0, medium: 0, low: 0 }} />);
    const bar = screen.getByTestId("severity-bar");
    expect(bar.children).toHaveLength(0);
  });
});

describe("illustrations and icons", () => {
  it("renders the hero illustration as a decorative svg", () => {
    const { container } = render(<HeroIllustration />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).toHaveAttribute("viewBox", "0 0 480 200");
  });

  it.each([
    ["CodeInIcon", <CodeInIcon key="code" />],
    ["ScanIcon", <ScanIcon key="scan" />],
    ["ReportIcon", <ReportIcon key="report" />],
    ["KeyIcon", <KeyIcon key="key" />],
    ["InjectionIcon", <InjectionIcon key="injection" />],
    ["LockIcon", <LockIcon key="lock" />],
    ["PackageIcon", <PackageIcon key="package" />],
    ["GlobeIcon", <GlobeIcon key="globe" />],
    ["ShieldScriptIcon", <ShieldScriptIcon key="shield" />],
  ])("renders %s as a decorative svg", (_name, icon) => {
    const { container } = render(icon);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });
});
