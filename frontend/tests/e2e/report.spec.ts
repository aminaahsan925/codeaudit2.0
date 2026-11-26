import { expect, test, type Page, type Route } from "@playwright/test";

import { reportPayload, runPayload, RUN_ID, SHARE_TOKEN } from "./fixtures";

// New routes compile on first hit in dev; allow extra time for that.
test.setTimeout(60_000);

const CORS = { "access-control-allow-origin": "*" };

async function mockHealthOk(page: Page) {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: CORS,
      body: JSON.stringify({ status: "ok", version: "0.1.0" }),
    }),
  );
}

function jsonResponse(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    headers: CORS,
    body: JSON.stringify(body),
  });
}

async function mockReport(page: Page) {
  await page.route(`**/api/runs/${RUN_ID}`, (route) =>
    jsonResponse(route, runPayload()),
  );
  await page.route(`**/api/reports/shared/${SHARE_TOKEN}`, (route) =>
    jsonResponse(route, reportPayload()),
  );
}

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await mockHealthOk(page);
});

test.describe("report page", () => {
  test("renders verdict, score, counts and findings", async ({ page }) => {
    await mockReport(page);
    await page.goto(`/reports/${RUN_ID}`);

    await expect(
      page.getByRole("heading", { level: 1, name: "pocket-notes" }),
    ).toBeVisible();
    await expect(page.getByText("Fix first", { exact: true })).toBeVisible();
    await expect(page.getByText("4.3")).toBeVisible();
    await expect(
      page.getByText("2 findings, most damaging first."),
    ).toBeVisible();
    await expect(
      page.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
    await expect(
      page.getByText("Pages are served without a Content-Security-Policy"),
    ).toBeVisible();
    await expect(page.getByText("Journey through the live app")).toBeVisible();
  });

  test("expands a finding to show its proof", async ({ page }) => {
    await mockReport(page);
    await page.goto(`/reports/${RUN_ID}`);

    await expect(
      page.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Show proof" }).first().click();

    await expect(page.getByText("Code")).toBeVisible();
    await expect(page.getByText(/const adminKey/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Why it matters" })).toBeVisible();
  });

  test("shows the share link and PDF link", async ({ page }) => {
    await mockReport(page);
    await page.goto(`/reports/${RUN_ID}`);

    const shareInput = page.getByLabel("Share link");
    await expect(shareInput).toHaveValue(`http://localhost:3000/r/${SHARE_TOKEN}`);
    await expect(page.getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      `http://localhost:8000/api/runs/${RUN_ID}/report.pdf?token=${SHARE_TOKEN}`,
    );
  });

  test("shows a not-found state for an unknown run", async ({ page }) => {
    await page.route(`**/api/runs/${RUN_ID}`, (route) =>
      jsonResponse(
        route,
        { error: { code: "not_found", message: "Audit run not found." } },
        404,
      ),
    );
    await page.goto(`/reports/${RUN_ID}`);

    await expect(page.getByText("This report was not found")).toBeVisible();
  });
});

test.describe("shared report page", () => {
  test("loads by token without touching the run endpoint", async ({ page }) => {
    let runEndpointCalled = false;
    await page.route(`**/api/runs/${RUN_ID}`, (route) => {
      runEndpointCalled = true;
      return route.abort("blockedbyclient");
    });
    await page.route(`**/api/reports/shared/${SHARE_TOKEN}`, (route) =>
      jsonResponse(route, reportPayload()),
    );

    await page.goto(`/r/${SHARE_TOKEN}`);

    await expect(
      page.getByRole("heading", { level: 1, name: "pocket-notes" }),
    ).toBeVisible();
    await expect(page.getByText("Fix first", { exact: true })).toBeVisible();
    await expect(
      page.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
    expect(runEndpointCalled).toBe(false);
  });

  test("shows a not-found state for an unknown token", async ({ page }) => {
    await page.route("**/api/reports/shared/bad-token", (route) =>
      jsonResponse(
        route,
        { error: { code: "not_found", message: "Report not found." } },
        404,
      ),
    );
    await page.goto("/r/bad-token");

    await expect(page.getByText("This report was not found")).toBeVisible();
  });
});
