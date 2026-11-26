import { expect, test, type Page, type Request } from "@playwright/test";

/**
 * CORS headers that mirror the real API. The app sends the session cookie
 * with every call (credentials: "include"), and browsers reject credentialed
 * responses whose Access-Control-Allow-Origin is "*": the mock must echo the
 * page origin and allow credentials, exactly like the backend does.
 */
function corsHeaders(request: Request): Record<string, string> {
  return {
    "access-control-allow-origin":
      request.headers()["origin"] ?? "http://localhost:3000",
    "access-control-allow-credentials": "true",
    "access-control-allow-methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "access-control-allow-headers": "Authorization, Content-Type",
    vary: "Origin",
  };
}

async function mockHealthOk(page: Page) {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: corsHeaders(route.request()),
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
      page.getByRole("heading", { level: 1, name: "Find out if your app is safe to launch." }),
    ).toBeVisible();
    await expect(page.getByRole("figure", { name: /a fictional app\.$/ })).toBeVisible();

    const hero = page.getByRole("region", { name: "Find out if your app is safe to launch." });
    await hero.getByRole("link", { name: "Run an audit" }).click();
    // The audit route compiles on first hit in dev; allow extra time.
    await expect(page).toHaveURL(/\/audits\/new$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Run an audit" })).toBeVisible();
  });
});

test.describe("API health badge", () => {
  // The badge lives in the app sidebar; the marketing page does not show it.
  test("shows online when the API reports ok", async ({ page }) => {
    await mockHealthOk(page);
    await page.goto("/reports");

    await expect(page.getByRole("button", { name: "API online" })).toBeVisible();
    await expect(page.getByRole("status")).toHaveText("LaunchAudit API online");
  });

  test("shows offline when the API returns 503", async ({ page }) => {
    await page.route("**/api/health", (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        headers: corsHeaders(route.request()),
        body: JSON.stringify({
          error: { code: "internal_error", message: "Service unavailable" },
        }),
      }),
    );
    await page.goto("/reports");

    await expect(page.getByRole("button", { name: "API offline" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("status")).toHaveText("LaunchAudit API offline");
  });

  test("shows offline when the request is aborted", async ({ page }) => {
    await page.route("**/api/health", (route) => route.abort("connectionrefused"));
    await page.goto("/reports");

    await expect(page.getByRole("button", { name: "API offline" })).toBeVisible({
      timeout: 15_000,
    });
  });
});

test.describe("navigation", () => {
  test("sidebar goes to Reports and marks it current", async ({ page }) => {
    await mockHealthOk(page);
    await page.goto("/audits/new");

    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.getByRole("link", { name: "New audit" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await nav.getByRole("link", { name: "Reports" }).click();

    await expect(page).toHaveURL(/\/reports$/);
    await expect(page.getByRole("heading", { level: 2, name: "No reports yet" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Reports" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await expect(
      page.getByRole("navigation", { name: "Breadcrumb" }).getByText("Reports"),
    ).toHaveAttribute("aria-current", "page");
  });

  test("sidebar collapses to a rail and stays collapsed after reload", async ({ page }) => {
    await mockHealthOk(page);
    await page.goto("/reports");

    await page.getByRole("button", { name: "Collapse sidebar" }).click();
    const expand = page.getByRole("button", { name: "Expand sidebar" });
    await expect(expand).toBeVisible();
    await expect(
      page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Reports" }),
    ).toHaveAttribute("aria-current", "page");

    await page.reload();
    await expect(expand).toBeVisible();
    await expand.click();
    await expect(page.getByRole("button", { name: "Collapse sidebar" })).toBeVisible();
  });

  test("command palette opens with the keyboard and navigates", async ({ page }) => {
    await mockHealthOk(page);
    await page.goto("/audits/new");

    await page.keyboard.press("ControlOrMeta+k");
    const dialog = page.getByRole("dialog", { name: "Search" });
    await expect(dialog).toBeVisible();

    const input = dialog.getByRole("combobox", { name: "Search actions and reports" });
    await expect(input).toBeFocused();
    await input.fill("reports");
    await page.keyboard.press("Enter");

    await expect(page).toHaveURL(/\/reports$/);
    await expect(dialog).toBeHidden();
  });

  test.describe("mobile viewport", () => {
    test.use({ viewport: { width: 390, height: 844 } });

    test("opens the menu and navigates", async ({ page }) => {
      await mockHealthOk(page);
      await page.goto("/audits/new");

      await expect(page.getByRole("navigation", { name: "Main" })).toBeHidden();
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
    await page.goto("/reports");

    const html = page.locator("html");
    await expect(html).not.toHaveClass(/(^|\s)dark(\s|$)/);

    await page.getByRole("button", { name: "Switch to dark theme" }).click();
    await expect(html).toHaveClass(/(^|\s)dark(\s|$)/);

    await page.getByRole("button", { name: "Switch to light theme" }).click();
    await expect(html).not.toHaveClass(/(^|\s)dark(\s|$)/);
  });
});
