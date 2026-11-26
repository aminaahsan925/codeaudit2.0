import { render, screen } from "@testing-library/react";
import { Inbox } from "lucide-react";
import { describe, expect, it, vi } from "vitest";

import NewAuditPage from "@/app/audits/new/page";
import ReportsPage from "@/app/reports/page";
import { EmptyState } from "@/components/empty-state";

import { renderWithQueryClient } from "./test-utils";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
}));

describe("EmptyState", () => {
  it("renders an h2 title, body and actions by default", () => {
    render(
      <EmptyState icon={Inbox} title="Nothing here" actions={<a href="/x">Do it</a>}>
        <p>Some explanation</p>
      </EmptyState>,
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "Nothing here" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Some explanation")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Do it" })).toHaveAttribute("href", "/x");
  });

  it("supports an h3 heading level", () => {
    render(
      <EmptyState icon={Inbox} title="Sub" headingLevel={3}>
        body
      </EmptyState>,
    );
    expect(screen.getByRole("heading", { level: 3, name: "Sub" })).toBeInTheDocument();
  });

  it("omits actions when none are given", () => {
    render(
      <EmptyState icon={Inbox} title="T">
        body
      </EmptyState>,
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("empty pages", () => {
  it("/reports shows its page and empty-state headings", () => {
    renderWithQueryClient(<ReportsPage />);
    expect(screen.getByRole("heading", { level: 1, name: "Reports" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "No reports yet" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Run an audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
  });

  it("/audits/new shows the audit form", () => {
    renderWithQueryClient(<NewAuditPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Run an audit" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Project name")).toBeInTheDocument();
    expect(screen.getByLabelText("GitHub repo URL")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run audit" })).toBeInTheDocument();
  });
});
