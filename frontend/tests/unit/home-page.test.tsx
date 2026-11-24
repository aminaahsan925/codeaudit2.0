import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "@/app/page";

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({ user: null, isSignedIn: false }),
  useProviders: () => ({
    isPending: false,
    isError: false,
    data: { google: false, demo: true },
  }),
  useDemoLogin: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  }),
}));

describe("HomePage", () => {
  it("renders the headline, hero graphic, actions and demo sign-in", () => {
    render(<HomePage />);

    expect(screen.getByText("Check your app before you launch it.")).toBeVisible();
    expect(screen.getByTestId("hero-illustration")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Run an audit" })).toHaveAttribute(
      "href",
      "/audits/new",
    );
    expect(screen.getByRole("link", { name: "View reports" })).toHaveAttribute(
      "href",
      "/reports",
    );
    expect(screen.getByRole("button", { name: "Demo sign-in" })).toBeVisible();
    expect(screen.getByText("Launch Report for pocket-notes")).toBeVisible();
  });

  it("shows the audit as a visual three-step flow with icons", () => {
    const { container } = render(<HomePage />);
    // Scope to the how section: the sample report also renders an <ol>
    // (the proof trace of the first finding).
    const section = container.querySelector('section[aria-labelledby="how-title"]');
    const steps = section?.querySelector("ol");
    const items = steps ? within(steps).getAllByRole("listitem") : [];
    expect(items).toHaveLength(3);
    for (const item of items) {
      expect(item.querySelector("svg")).not.toBeNull();
    }
    expect(screen.getByText("Add your code")).toBeVisible();
    expect(screen.getByText("Add your live URL")).toBeVisible();
    expect(screen.getByText("Press Run")).toBeVisible();
  });

  it("shows the six checks as icon cards with one short line each", () => {
    const { container } = render(<HomePage />);
    const section = container.querySelector(
      'section[aria-labelledby="checks-title"]',
    );
    const cards = section ? section.querySelector("ul") : null;
    const items = cards ? within(cards).getAllByRole("listitem") : [];
    expect(items).toHaveLength(6);
    for (const item of items) {
      expect(item.querySelector("svg")).not.toBeNull();
    }
    for (const title of [
      "Leaked secrets",
      "Injection",
      "Login and access control",
      "Vulnerable dependencies",
      "Live configuration",
      "Request forgery and XSS",
    ]) {
      expect(screen.getByText(title)).toBeVisible();
    }
  });
});
