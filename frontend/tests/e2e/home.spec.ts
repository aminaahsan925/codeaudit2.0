import { expect, test, type Page } from "@playwright/test";

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

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
});

test.describe("landing page", () => {
  test("shows the hero and navigates to the audit page", async ({ page }) => {
    await mockHealthOk(page);
    await page.goto("/");

    await expect(
      page.getByRole("heading", { level: 1, name: "Check your app before you launch it." }),
    ).toBeVisible();

    await page.getByRole("link", { name: "Run an audit" }).first().click();
    await expect(page).toHaveURL(/\/audits\/new$/);
    await expect(page.getByRole("heading", { level: 1, name: "Run an audit" })).toBeVisible();
  });
});

test.describe("API health badge", () => {
  test("shows online when the API reports ok", async ({ page }) => {
    await mockHealthOk(page);
    await page.goto("/");

    await expect(page.getByRole("button", { name: "API online" })).toBeVisible();
    await expect(page.getByRole("status")).toHaveText("LaunchAudit API online");
  });

  test("shows offline when the API returns 503", async ({ page }) => {
    await page.route("**/api/health", (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        headers: CORS,
        body: JSON.stringify({
          error: { code: "internal_error", message: "Service unavailable" },
        }),
      }),
    );
    await page.goto("/");

    await expect(page.getByRole("button", { name: "API offline" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("status")).toHaveText("LaunchAudit API offline");
  });

  test("shows offline when the request is aborted", async ({ page }) => {
    await page.route("**/api/health", (route) => route.abort("connectionrefused"));
    await page.goto("/");

    await expect(page.getByRole("button", { name: "API offline" })).toBeVisible({
      timeout: 15_000,
    });
  });
});

test.describe("navigation", () => {
  test("desktop nav goes to Reports and marks it current", async ({ page }) => {
    await mockHealthOk(page);
    await page.goto("/");

    const nav = page.getByRole("navigation", { name: "Main" });
    await nav.getByRole("link", { name: "Reports" }).click();

    await expect(page).toHaveURL(/\/reports$/);
    await expect(page.getByRole("heading", { level: 2, name: "No reports yet" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Reports" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  test.describe("mobile viewport", () => {
    test.use({ viewport: { width: 390, height: 844 } });

    test("opens the menu and navigates", async ({ page }) => {
      await mockHealthOk(page);
      await page.goto("/");

      await expect(
        page.getByRole("banner").getByRole("link", { name: "Reports" }),
      ).toBeHidden();
      await page.getByRole("button", { name: "Open menu" }).click();

      const dialog = page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      await dialog.getByRole("link", { name: "Reports" }).click();

      await expect(page).toHaveURL(/\/reports$/);
      await expect(page.getByRole("heading", { level: 1, name: "Reports" })).toBeVisible();
      await expect(page.getByRole("dialog")).toBeHidden();
    });
  });
});

test.describe("theme", () => {
  test("toggle switches the dark class on html", async ({ page }) => {
    await mockHealthOk(page);
    await page.goto("/");

    const html = page.locator("html");
    await expect(html).not.toHaveClass(/(^|\s)dark(\s|$)/);

    await page.getByRole("button", { name: "Switch to dark theme" }).click();
    await expect(html).toHaveClass(/(^|\s)dark(\s|$)/);

    await page.getByRole("button", { name: "Switch to light theme" }).click();
    await expect(html).not.toHaveClass(/(^|\s)dark(\s|$)/);
  });
});
