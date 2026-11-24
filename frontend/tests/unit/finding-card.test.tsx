import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { FindingCard, findingLocation } from "@/components/finding-card";

import { makeFinding, RUN_ID } from "./fixtures";
import { renderWithQueryClient } from "./test-utils";

describe("findingLocation", () => {
  it("formats file and line", () => {
    expect(findingLocation(makeFinding())).toBe("src/lib/db.ts:4");
  });

  it("formats a line range", () => {
    expect(findingLocation(makeFinding({ start_line: 4, end_line: 6 }))).toBe(
      "src/lib/db.ts:4-6",
    );
  });

  it("returns null without a file", () => {
    expect(
      findingLocation(makeFinding({ file: null, start_line: null, end_line: null })),
    ).toBeNull();
  });
});

describe("FindingCard", () => {
  it("shows severity, title and location collapsed", () => {
    renderWithQueryClient(<FindingCard finding={makeFinding()} index={1} runId={RUN_ID} />);
    expect(screen.getByText("Critical")).toBeVisible();
    expect(
      screen.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
    expect(screen.getByText("src/lib/db.ts:4")).toBeVisible();
    expect(screen.getByRole("button", { name: "Show proof" })).toBeVisible();
    expect(screen.queryByText("Code")).not.toBeInTheDocument();
  });

  it("expands to show snippet, trace, evidence, AI verdict and fix guidance", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <FindingCard
        finding={makeFinding({
          trace: [
            {
              file: "src/routes/notes.ts",
              line: 12,
              snippet: "const id = req.params.id;",
              label: "User input enters here",
            },
            {
              file: "src/db/notes.ts",
              line: 8,
              snippet: "db.query(`SELECT * FROM notes WHERE id = ${id}`)",
              label: "Input reaches the query",
            },
          ],
          evidence: {
            http: {
              method: "GET",
              url: "https://app.example.com/api/notes/1042",
              status: 200,
              request_headers: { cookie: "session=abc" },
              response_headers: { "content-type": "application/json" },
              body_excerpt: '{"note": "someone else\'s"}',
            },
          },
          ai_verdict: {
            verdict: "confirmed",
            reason: "The query builds SQL from the id parameter.",
            quoted_code: "db.query(`SELECT * FROM notes WHERE id = ${id}`)",
          },
        })}
        index={2}
        runId={RUN_ID}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Show proof" }));

    expect(screen.getByText("Code")).toBeVisible();
    expect(screen.getByText(/const adminKey/)).toBeVisible();
    expect(screen.getByText("Data flow")).toBeVisible();
    expect(screen.getByText("User input enters here")).toBeVisible();
    expect(screen.getByText("Live request")).toBeVisible();
    expect(screen.getByText(/\/api\/notes\/1042/)).toBeVisible();
    expect(screen.getByText("Review: Confirmed")).toBeVisible();
    expect(screen.getByText("How to fix it")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Why it matters" })).toBeVisible();
  });

  it("renders package evidence and secret previews", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <FindingCard
        finding={makeFinding({
          evidence: {
            package: { name: "lodash", version: "4.17.20", advisory: "GHSA-123" },
            secret_preview: "sk_live_••••",
          },
        })}
        index={1}
        runId={RUN_ID}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Show proof" }));
    expect(screen.getByText("Package")).toBeVisible();
    expect(screen.getByText(/lodash 4.17.20/)).toBeVisible();
    expect(screen.getByText("GHSA-123", { exact: false })).toBeVisible();
    expect(screen.getByText("Secret preview")).toBeVisible();
    expect(screen.getByText("sk_live_••••")).toBeVisible();
  });

  it("renders a screenshot from evidence when present", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <FindingCard
        finding={makeFinding({
          evidence: { screenshot_url: `/api/runs/${RUN_ID}/artifacts/checkout.png` },
        })}
        index={1}
        runId={RUN_ID}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Show proof" }));
    const img = screen.getByAltText("Screenshot captured during the audit");
    expect(img).toHaveAttribute(
      "src",
      `http://localhost:8000/api/runs/${RUN_ID}/artifacts/checkout.png`,
    );
  });

  it("hides the proof again on a second click", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<FindingCard finding={makeFinding()} index={1} runId={RUN_ID} />);
    await user.click(screen.getByRole("button", { name: "Show proof" }));
    expect(screen.getByText("Code")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Hide proof" }));
    expect(screen.queryByText("Code")).not.toBeInTheDocument();
  });
});
