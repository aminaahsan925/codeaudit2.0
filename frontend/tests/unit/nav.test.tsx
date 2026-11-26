import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { CommandPalette } from "@/components/shell/command-palette";
import { MobileNav } from "@/components/shell/mobile-nav";
import { ShellProvider, SIDEBAR_STORAGE_KEY } from "@/components/shell/shell-context";
import { Sidebar } from "@/components/shell/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { RunsHistory } from "@/hooks/use-runs-history";
import { getBreadcrumbs, isActivePath } from "@/lib/nav";

const pathname = vi.hoisted(() => ({ value: "/" }));
const push = vi.hoisted(() => vi.fn());
const history = vi.hoisted(() => ({ value: { entries: [] } as RunsHistory }));

vi.mock("next/navigation", () => ({
  usePathname: () => pathname.value,
  useRouter: () => ({ push }),
}));
vi.mock("@/hooks/use-health", () => ({
  useHealth: () => ({
    status: "success",
    data: { status: "ok", version: "1.0.0" },
    error: null,
    isFetching: false,
    refetch: vi.fn(),
  }),
}));
vi.mock("@/hooks/use-runs-history", () => ({ useRunsHistory: () => history.value }));

function renderInShell(ui: ReactElement) {
  return render(
    <ShellProvider>
      <TooltipProvider>{ui}</TooltipProvider>
    </ShellProvider>,
  );
}

beforeEach(() => {
  pathname.value = "/";
  push.mockReset();
  history.value = { entries: [] };
  window.localStorage.clear();
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

describe("getBreadcrumbs", () => {
  it.each([
    ["/", []],
    ["/reports", [{ label: "Reports" }]],
    ["/reports/run_123", [{ label: "Reports", href: "/reports" }, { label: "Report" }]],
    ["/audits/new", [{ label: "New audit" }]],
    ["/audits/run_123", [{ label: "Audit run" }]],
    ["/r/tok_abc", [{ label: "Shared report" }]],
    ["/sign-in", [{ label: "Sign in" }]],
    ["/sign-in/extra", [{ label: "Page not found" }]],
    ["/does-not-exist", [{ label: "Page not found" }]],
  ])("labels %s", (path, expected) => {
    expect(getBreadcrumbs(path)).toEqual(expected);
  });
});

describe("Sidebar", () => {
  it("links to the audit, reports and help pages", () => {
    renderInShell(<Sidebar />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "New audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
    expect(within(nav).getByRole("link", { name: "Reports" })).toHaveAttribute(
      "href",
      "/reports",
    );
    expect(within(nav).getByRole("link", { name: "Help" })).toHaveAttribute("href", "/#faq");
  });

  it("lists only New audit, Reports and Help, with no unbuilt items", () => {
    renderInShell(<Sidebar />);
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "New audit",
      "Reports",
      "Help",
    ]);
    expect(within(nav).queryByRole("button")).not.toBeInTheDocument();
    expect(nav).not.toHaveTextContent(/Projects|Settings|Soon/);
  });

  it("marks no link current on the home page", () => {
    renderInShell(<Sidebar />);
    for (const link of screen.getAllByRole("link")) {
      expect(link).not.toHaveAttribute("aria-current");
    }
  });

  it("marks the active link with aria-current=page", () => {
    pathname.value = "/reports";
    renderInShell(<Sidebar />);
    expect(screen.getByRole("link", { name: "Reports" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "New audit" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("keeps the parent active on nested routes", () => {
    pathname.value = "/audits/new/step-2";
    renderInShell(<Sidebar />);
    expect(screen.getByRole("link", { name: "New audit" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("shows the API status and the read-only note", () => {
    renderInShell(<Sidebar />);
    expect(screen.getByRole("button", { name: "API online" })).toBeInTheDocument();
    expect(screen.getByText("Your code is read, never run.")).toBeInTheDocument();
  });

  it("collapses to a rail, keeps link names, and remembers the choice", async () => {
    pathname.value = "/reports";
    const user = userEvent.setup();
    renderInShell(<Sidebar />);

    const toggle = screen.getByRole("button", { name: "Collapse sidebar" });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await user.click(toggle);

    expect(window.localStorage.getItem(SIDEBAR_STORAGE_KEY)).toBe("1");
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.getByRole("link", { name: "Reports" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "LaunchAudit home" })).toHaveAttribute("href", "/");
    expect(screen.queryByText("Your code is read, never run.")).not.toBeInTheDocument();
  });

  it("starts collapsed when the choice was stored", () => {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, "1");
    renderInShell(<Sidebar />);
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();
  });
});

describe("MobileNav", () => {
  it("opens a drawer with the same links and closes on selection", async () => {
    pathname.value = "/audits/new";
    const user = userEvent.setup();
    renderInShell(<MobileNav />);

    expect(screen.queryByRole("link", { name: "Reports" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open menu" }));

    const dialog = await screen.findByRole("dialog");
    const reports = within(dialog).getByRole("link", { name: "Reports" });
    expect(reports).toHaveAttribute("href", "/reports");
    expect(within(dialog).queryByText(/Projects|Settings|Soon/)).not.toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: "New audit" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(reports);
    await vi.waitFor(() =>
      expect(screen.queryByRole("link", { name: "Reports" })).not.toBeInTheDocument(),
    );
  });
});

describe("Breadcrumbs", () => {
  it("shows labels, not ids, with the parent as a link", () => {
    pathname.value = "/reports/run_8f2a";
    render(<Breadcrumbs />);
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(nav).getByRole("link", { name: "Reports" })).toHaveAttribute(
      "href",
      "/reports",
    );
    expect(within(nav).getByText("Report")).toHaveAttribute("aria-current", "page");
    expect(nav).not.toHaveTextContent("run_8f2a");
  });

  it("renders nothing on the home page", () => {
    render(<Breadcrumbs />);
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });
});

describe("CommandPalette", () => {
  it("opens with Ctrl+K and runs the highlighted action with Enter", async () => {
    const user = userEvent.setup();
    renderInShell(<CommandPalette />);

    await user.keyboard("{Control>}k{/Control}");
    const dialog = await screen.findByRole("dialog", { name: "Search" });
    const input = within(dialog).getByRole("combobox", { name: "Search actions and reports" });
    await vi.waitFor(() => expect(input).toHaveFocus());

    const options = within(dialog).getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual(
      expect.arrayContaining([
        expect.stringContaining("New audit"),
        expect.stringContaining("View reports"),
        expect.stringContaining("Switch theme"),
        expect.stringContaining("Help"),
      ]),
    );
    expect(input).toHaveAttribute("aria-activedescendant", options[0]?.id);

    await user.keyboard("{ArrowDown}");
    expect(input).toHaveAttribute("aria-activedescendant", options[1]?.id);
    expect(options[1]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{Enter}");
    expect(push).toHaveBeenCalledWith("/reports");
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("opens with / and lists recent reports", async () => {
    history.value = {
      entries: [
        {
          stored: { id: "run_1", projectName: "Acme shop", createdAt: "2026-11-20T10:00:00Z" },
          run: undefined,
          isLoading: true,
          isError: false,
        },
      ],
    };
    const user = userEvent.setup();
    renderInShell(<CommandPalette />);

    await user.keyboard("/");
    const dialog = await screen.findByRole("dialog", { name: "Search" });
    const group = within(dialog).getByRole("group", { name: "Recent reports" });
    await user.type(within(dialog).getByRole("combobox"), "acme");
    const option = within(group).getByRole("option", { name: /Acme shop/ });
    await user.click(option);
    expect(push).toHaveBeenCalledWith("/audits/run_1");
  });

  it("shows an empty state when nothing matches and closes with Escape", async () => {
    const user = userEvent.setup();
    renderInShell(<CommandPalette />);

    await user.keyboard("{Control>}k{/Control}");
    const dialog = await screen.findByRole("dialog", { name: "Search" });
    await user.type(within(dialog).getByRole("combobox"), "zzz");

    expect(within(dialog).queryByRole("option")).not.toBeInTheDocument();
    expect(within(dialog).getByText('Nothing matches "zzz"')).toBeInTheDocument();
    expect(within(dialog).getByRole("status")).toHaveTextContent("0 results");

    await user.keyboard("{Escape}");
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
