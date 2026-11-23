import { describe, expect, it } from "vitest";

import {
  formatRiskScore,
  isActiveRunStatus,
  isTerminalRunStatus,
  scoreChangeLabel,
} from "@/lib/report";

describe("formatRiskScore", () => {
  it.each([
    [0, "0.0"],
    [4.25, "4.3"],
    [10, "10.0"],
    [10.4, "10.0"],
    [-1, "0.0"],
  ])("formats %s as %s", (score, expected) => {
    expect(formatRiskScore(score)).toBe(expected);
  });
});

describe("run status helpers", () => {
  it("treats queued and running as active", () => {
    expect(isActiveRunStatus("queued")).toBe(true);
    expect(isActiveRunStatus("running")).toBe(true);
    expect(isActiveRunStatus("succeeded")).toBe(false);
    expect(isActiveRunStatus("failed")).toBe(false);
    expect(isActiveRunStatus("cancelled")).toBe(false);
  });

  it("treats succeeded, failed and cancelled as terminal", () => {
    expect(isTerminalRunStatus("succeeded")).toBe(true);
    expect(isTerminalRunStatus("failed")).toBe(true);
    expect(isTerminalRunStatus("cancelled")).toBe(true);
    expect(isTerminalRunStatus("running")).toBe(false);
  });
});

describe("scoreChangeLabel", () => {
  it("returns null without a previous run", () => {
    expect(scoreChangeLabel(null)).toBeNull();
  });

  it("reads a negative change as an improvement", () => {
    expect(scoreChangeLabel(-2.3)).toBe("Risk score down 2.3 since the last run.");
  });

  it("reads a positive change as a worsening", () => {
    expect(scoreChangeLabel(0.5)).toBe("Risk score up 0.5 since the last run.");
  });

  it("reads zero as unchanged", () => {
    expect(scoreChangeLabel(0)).toBe("Risk score unchanged since the last run.");
  });
});
