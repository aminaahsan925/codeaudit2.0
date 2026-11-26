import { expect, test, type Page, type Route } from "@playwright/test";

import { NEW_RUN_ID, reportPayload, runPayload, RUN_ID, SHARE_TOKEN } from "./fixtures";

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

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await mockHealthOk(page);
});

test.describe("new audit form", () => {
  test("shows validation errors without submitting", async ({ page }) => {
    await page.goto("/audits/new");

    await page.getByRole("button", { name: "Run audit" }).click();

    await expect(page.getByText("Enter a project name.")).toBeVisible();
    await expect(
      page.getByText("Add a GitHub repo URL or upload a zip file.").first(),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/audits\/new$/);
  });

  test("submits and navigates to the run page, then to the report", async ({ page }) => {
    let runCalls = 0;
    await page.route("**/api/runs", (route) => {
      if (route.request().method() === "POST") {
        return jsonResponse(route, runPayload({ status: "queued", progress: 0 }), 201);
      }
      return route.abort("blockedbyclient");
    });
    await page.route(`**/api/runs/${RUN_ID}`, (route) => {
      runCalls += 1;
      // The first polls see the run in progress; later polls see it done.
      if (runCalls <= 2) {
        return jsonResponse(route, runPayload({ status: "running", progress: 40 }));
      }
      return jsonResponse(route, runPayload({ status: "succeeded", progress: 100 }));
    });
    await page.route(`**/api/reports/shared/${SHARE_TOKEN}`, (route) =>
      jsonResponse(route, reportPayload()),
    );

    await page.goto("/audits/new");
    await page.getByLabel("Project name").fill("pocket-notes");
    await page
      .getByLabel("GitHub repo URL")
      .fill("https://github.com/example/pocket-notes");
    await page.getByRole("button", { name: "Run audit" }).click();

    await expect(page).toHaveURL(`/audits/${RUN_ID}`, { timeout: 15_000 });
    await expect(
      page.getByRole("heading", { level: 1, name: "Audit: pocket-notes" }),
    ).toBeVisible();
    await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "40");

    await expect(page.getByText("Audit complete")).toBeVisible({ timeout: 15_000 });
    await page.getByRole("link", { name: "View the Launch Report" }).click();

    await expect(page).toHaveURL(`/reports/${RUN_ID}`, { timeout: 15_000 });
    await expect(page.getByText("Fix first", { exact: true })).toBeVisible();
    await expect(
      page.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();
  });

  test("shows the API error when the audit cannot start", async ({ page }) => {
    await page.route("**/api/runs", (route) => {
      if (route.request().method() === "POST") {
        return jsonResponse(
          route,
          { error: { code: "bad_request", message: "Too many audits this hour." } },
          429,
        );
      }
      return route.abort("blockedbyclient");
    });

    await page.goto("/audits/new");
    await page.getByLabel("Project name").fill("pocket-notes");
    await page
      .getByLabel("GitHub repo URL")
      .fill("https://github.com/example/pocket-notes");
    await page.getByRole("button", { name: "Run audit" }).click();

    await expect(
      page.getByText("The audit could not start: Too many audits this hour."),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/audits\/new$/);
  });
});

test.describe("history", () => {
  test("a created run appears on the reports page", async ({ page }) => {
    await page.route("**/api/runs", (route) => {
      if (route.request().method() === "POST") {
        return jsonResponse(route, runPayload({ status: "queued", progress: 0 }), 201);
      }
      return route.abort("blockedbyclient");
    });
    await page.route(`**/api/runs/${RUN_ID}`, (route) =>
      jsonResponse(route, runPayload({ status: "succeeded", progress: 100 })),
    );

    await page.goto("/audits/new");
    await page.getByLabel("Project name").fill("pocket-notes");
    await page
      .getByLabel("GitHub repo URL")
      .fill("https://github.com/example/pocket-notes");
    await page.getByRole("button", { name: "Run audit" }).click();
    await expect(page).toHaveURL(`/audits/${RUN_ID}`, { timeout: 15_000 });

    await page.goto("/reports");
    await expect(
      page.getByRole("link", { name: "View the Launch Report for pocket-notes" }),
    ).toBeVisible();
  });
});

test.describe("rerun", () => {
  test("rerunning from the report navigates to the new run", async ({ page }) => {
    await page.route(`**/api/runs/${RUN_ID}`, (route) =>
      jsonResponse(route, runPayload()),
    );
    await page.route(`**/api/reports/shared/${SHARE_TOKEN}`, (route) =>
      jsonResponse(route, reportPayload()),
    );
    await page.route(`**/api/runs/${RUN_ID}/rerun`, (route) => {
      // The JSON rerun POST sends a CORS preflight first.
      if (route.request().method() === "OPTIONS") {
        return route.fulfill({
          status: 204,
          headers: {
            ...CORS,
            "access-control-allow-methods": "POST, OPTIONS",
            "access-control-allow-headers": "content-type",
          },
        });
      }
      return jsonResponse(
        route,
        runPayload({ id: NEW_RUN_ID, status: "queued", progress: 0 }),
        201,
      );
    });
    await page.route(`**/api/runs/${NEW_RUN_ID}`, (route) =>
      jsonResponse(route, runPayload({ id: NEW_RUN_ID, status: "queued", progress: 0 })),
    );

    await page.goto(`/reports/${RUN_ID}`);
    await expect(
      page.getByText("Database admin key is shipped to the browser"),
    ).toBeVisible();

    await page.getByRole("button", { name: "Rerun audit" }).click();
    await expect(page).toHaveURL(`/audits/${NEW_RUN_ID}`, { timeout: 15_000 });
    await expect(page.getByText("Queued")).toBeVisible();
  });
});
