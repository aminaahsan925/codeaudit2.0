import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LazyMotion, MotionConfig, MotionGlobalConfig, domAnimation } from "motion/react";
import type { ReactElement } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { ReportView } from "@/components/report-view";

import { makeFinding, makeReport, makeRun, PREVIOUS_RUN_ID, RUN_ID, SHARE_TOKEN } from "./fixtures";
import { renderWithQueryClient } from "./test-utils";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// The report animates in (verdict pop, row stagger). Run it under the same
// motion providers as the app, with animations jumping to their end state.
beforeAll(() => {
  MotionGlobalConfig.skipAnimations = true;
});

function renderReport(ui: ReactElement) {
  return renderWithQueryClient(
    <LazyMotion features={domAnimation} strict>
      <MotionConfig reducedMotion="user">{ui}</MotionConfig>
    </LazyMotion>,
  );
}

describe("ReportView", () => {
  it("renders verdict, score, counts, findings and actions", async () => {
    const user = userEvent.setup();
    renderReport(<ReportView report={makeReport()} />);

    expect(screen.getByRole("heading", { level: 1, name: "pocket-notes" })).toBeVisible();
    await waitFor(() => expect(screen.getByText("Fix first")).toBeVisible());
    expect(screen.getByText(VERDICT_SENTENCE)).toBeVisible();
    await waitFor(() => expect(screen.getByText("4.3")).toBeVisible());
    // "Critical" appears in the severity legend and on the finding's badge.
    expect(screen.getAllByText("Critical")).toHaveLength(2);
    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "A secret value is written into your code",
      }),
    ).toBeVisible();
    expect(
      screen.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
    expect(screen.getByText("1 problem, most serious first.", { exact: false })).toBeVisible();

    // Info tips on the verdict, the score, the severity and the CWE.
    expect(screen.getByRole("button", { name: "What is Verdict?" })).toBeVisible();
    expect(screen.getByRole("button", { name: "What is Risk score?" })).toBeVisible();
    expect(screen.getByRole("button", { name: "What is Critical severity?" })).toBeVisible();
    expect(screen.getByRole("button", { name: "What is CWE?" })).toBeVisible();

    expect(screen.getByRole("button", { name: "Rerun audit" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      `http://localhost:8000/api/runs/${RUN_ID}/report.pdf?token=${SHARE_TOKEN}`,
    );
    await user.click(screen.getByRole("button", { name: "Share" }));
    const shareInput = (await screen.findByLabelText("Share link")) as HTMLInputElement;
    expect(shareInput.value).toContain(`/r/${SHARE_TOKEN}`);
  });

  it("shows the empty-findings state when the audit found nothing", async () => {
    renderReport(
      <ReportView
        report={makeReport({
          run: makeRun({ verdict: "launch", risk_score: 0.0 }),
          findings: [],
          counts: { critical: 0, high: 0, medium: 0, low: 0 },
        })}
      />,
    );
    await waitFor(() => expect(screen.getByText("Launch")).toBeVisible());
    expect(screen.getByText("No problems found")).toBeVisible();
  });

  it("shows the rerun comparison with score change and fixed findings", async () => {
    const user = userEvent.setup();
    renderReport(
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
      screen.getByText("Risk score down 3.3 since the last run (4.3 to 1.0)."),
    ).toBeVisible();
    expect(screen.getByText("Problems fixed").nextElementSibling).toHaveTextContent("1");
    expect(screen.getByRole("heading", { name: "Fixed since the last run" })).toBeVisible();
    expect(screen.getByText("1 problem from the last run no longer shows up.")).toBeVisible();

    // The fixed group starts collapsed.
    expect(
      screen.queryByText("Database admin key is shipped to the browser"),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show fixed problems" }));
    expect(
      screen.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
  });

  it("shows journey steps when the run has them", () => {
    renderReport(
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

  it("explains the missing journey when the run has none", () => {
    renderReport(<ReportView report={makeReport({ journey_steps: [] })} />);
    expect(screen.getByText("Journey through the live app")).toBeVisible();
    expect(screen.getByText("No screenshots for this audit")).toBeVisible();
  });

  it("hides the PDF link and Share without a share token", () => {
    renderReport(
      <ReportView report={makeReport({ run: makeRun({ share_token: null }) })} />,
    );
    expect(screen.queryByRole("link", { name: "Download PDF" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Share" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Share link")).not.toBeInTheDocument();
  });

  it("is read only when shared: no rerun, a note and a call to action", () => {
    renderReport(<ReportView report={makeReport()} readOnly />);
    expect(screen.getByText("Shared report, read only")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Rerun audit" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Add journey login" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Run your own audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
    expect(screen.getByRole("link", { name: "Download PDF" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Share" })).toBeVisible();
  });
});

const VERDICT_SENTENCE =
  "There are problems to fix before launch. None of them are emergencies.";
