import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReportView } from "@/components/report-view";

import { makeFinding, makeReport, makeRun, PREVIOUS_RUN_ID, RUN_ID, SHARE_TOKEN } from "./fixtures";
import { renderWithQueryClient } from "./test-utils";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("ReportView", () => {
  it("renders verdict, score, counts, findings and actions", () => {
    renderWithQueryClient(<ReportView report={makeReport()} />);

    expect(screen.getByText("pocket-notes")).toBeVisible();
    expect(screen.getByText("Fix first")).toBeVisible();
    expect(screen.getByText("4.3")).toBeVisible();
    // "Critical" appears in the counts strip and on the finding's badge.
    expect(screen.getAllByText("Critical")).toHaveLength(2);
    expect(
      screen.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Rerun audit" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      `http://localhost:8000/api/runs/${RUN_ID}/report.pdf?token=${SHARE_TOKEN}`,
    );
    const shareInput = screen.getByLabelText("Share link") as HTMLInputElement;
    expect(shareInput.value).toContain(`/r/${SHARE_TOKEN}`);
  });

  it("shows the empty-findings state when the audit found nothing", () => {
    renderWithQueryClient(
      <ReportView
        report={makeReport({
          run: makeRun({ verdict: "launch", risk_score: 0.0 }),
          findings: [],
          counts: { critical: 0, high: 0, medium: 0, low: 0 },
        })}
      />,
    );
    expect(screen.getByText("Launch")).toBeVisible();
    expect(screen.getByText("No problems found")).toBeVisible();
  });

  it("shows the rerun comparison with score change and resolved findings", () => {
    renderWithQueryClient(
      <ReportView
        report={makeReport({
          run: makeRun({
            previous_run_id: PREVIOUS_RUN_ID,
            verdict: "launch",
            risk_score: 1.0,
          }),
          findings: [],
          counts: { critical: 0, high: 0, medium: 0, low: 0 },
          previous_risk_score: 4.3,
          score_change: -3.3,
          resolved_findings: [
            makeFinding({ title: "Database admin key is shipped to the browser" }),
          ],
        })}
      />,
    );

    expect(screen.getByText("Since the last run")).toBeVisible();
    expect(
      screen.getByText("Risk score down 3.3 since the last run."),
    ).toBeVisible();
    expect(screen.getByText(/1 finding resolved/)).toBeVisible();
    expect(
      screen.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
  });

  it("shows journey steps when the run has them", () => {
    renderWithQueryClient(
      <ReportView
        report={makeReport({
          journey_steps: [
            { name: "Sign up", status: "passed", screenshot_url: "signup.png", error: null },
          ],
        })}
      />,
    );
    expect(screen.getByText("Journey through the live app")).toBeVisible();
    expect(screen.getByText(/1\. Sign up/)).toBeVisible();
  });

  it("hides the PDF link without a share token", () => {
    renderWithQueryClient(
      <ReportView report={makeReport({ run: makeRun({ share_token: null }) })} />,
    );
    expect(screen.queryByRole("link", { name: "Download PDF" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Share link")).not.toBeInTheDocument();
  });
});
