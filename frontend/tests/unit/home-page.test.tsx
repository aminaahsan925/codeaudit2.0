import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

describe("HomePage hero", () => {
  it("leads with the LaunchAudit wordmark as the only h1, with a decorative mark", () => {
    render(<HomePage />);

    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toHaveAccessibleName("LaunchAudit");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(h1.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("keeps both calls to action in the hero", () => {
    render(<HomePage />);

    const hero = screen.getByRole("region", { name: "LaunchAudit" });
    expect(within(hero).getByRole("link", { name: "Run an audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
    expect(within(hero).getByRole("link", { name: "View reports" })).toHaveAttribute(
      "href",
      "/reports",
    );
  });

  it("no longer carries the old headline or description inside the hero", () => {
    render(<HomePage />);

    expect(screen.queryByText("Check your app before you launch it.")).not.toBeInTheDocument();
    const hero = screen.getByRole("region", { name: "LaunchAudit" });
    expect(within(hero).queryByText(/reads your code and probes your live URL/)).toBeNull();
    expect(within(hero).queryByText(/never executed/)).toBeNull();
  });

  it("puts the description section between the hero and How an audit works", () => {
    render(<HomePage />);

    const about = screen.getByRole("region", { name: "What LaunchAudit does" });
    expect(within(about).getByText(/reads your code and probes your live URL/)).toBeInTheDocument();
    expect(within(about).getByText(/Your code is read, never executed\./)).toBeInTheDocument();

    const headings = screen
      .getAllByRole("heading", { level: 2 })
      .map((heading) => heading.textContent);
    expect(headings.slice(0, 2)).toEqual(["What LaunchAudit does", "How an audit works"]);
  });
});
