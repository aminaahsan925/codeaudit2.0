import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MainNav } from "@/components/main-nav";
import { MobileNav } from "@/components/mobile-nav";
import { isActivePath } from "@/lib/nav";

const pathname = vi.hoisted(() => ({ value: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.value }));

beforeEach(() => {
  pathname.value = "/";
});

describe("isActivePath", () => {
  it.each([
    ["/reports", "/reports", true],
    ["/reports/123", "/reports", true],
    ["/reportsx", "/reports", false],
    ["/", "/reports", false],
  ])("isActivePath(%s, %s) = %s", (path, href, expected) => {
    expect(isActivePath(path, href)).toBe(expected);
  });
});

describe("MainNav", () => {
  it("links to the audit and reports pages", () => {
    render(<MainNav />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Run audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
    expect(within(nav).getByRole("link", { name: "Reports" })).toHaveAttribute(
      "href",
      "/reports",
    );
  });

  it("marks no link current on the home page", () => {
    render(<MainNav />);
    for (const link of screen.getAllByRole("link")) {
      expect(link).not.toHaveAttribute("aria-current");
    }
  });

  it("marks the active link with aria-current=page", () => {
    pathname.value = "/reports";
    render(<MainNav />);
    expect(screen.getByRole("link", { name: "Reports" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Run audit" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("keeps the parent active on nested routes", () => {
    pathname.value = "/audits/new/step-2";
    render(<MainNav />);
    expect(screen.getByRole("link", { name: "Run audit" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});

describe("MobileNav", () => {
  it("opens a menu with the same links and closes on selection", async () => {
    pathname.value = "/audits/new";
    const user = userEvent.setup();
    render(<MobileNav />);

    expect(screen.queryByRole("link", { name: "Reports" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open menu" }));

    const reports = await screen.findByRole("link", { name: "Reports" });
    expect(reports).toHaveAttribute("href", "/reports");
    expect(screen.getByRole("link", { name: "Run audit" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(reports);
    await vi.waitFor(() =>
      expect(screen.queryByRole("link", { name: "Reports" })).not.toBeInTheDocument(),
    );
  });
});
