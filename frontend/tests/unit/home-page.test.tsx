import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(marketing)/page";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingHeader } from "@/components/marketing/marketing-header";
import { formatRiskScore } from "@/lib/report";
import { SAMPLE_FINDINGS, SAMPLE_PREVIOUS_SCORE, SAMPLE_SCORE } from "@/lib/sample-data";

beforeEach(() => {
  // jsdom has no IntersectionObserver; scroll reveals need one to mount.
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() {
        return [];
      }
    },
  );
});

describe("HomePage", () => {
  it("has one h1 and sends the main call to action to a new audit", () => {
    render(<HomePage />);

    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent("Find out if your app is safe to launch.");

    const hero = screen.getByRole("region", { name: "Find out if your app is safe to launch." });
    expect(within(hero).getByRole("link", { name: "Run an audit" })).toHaveAttribute("href", "/audits/new");
    expect(within(hero).getByRole("link", { name: "See an example" })).toHaveAttribute("href", "#example");
  });

  it("labels the hero visual as an example and uses the sample score", () => {
    render(<HomePage />);

    expect(screen.getByText(/a fictional app\.$/)).toBeInTheDocument();
    const score = formatRiskScore(SAMPLE_SCORE);
    expect(screen.getAllByText(`Risk score: ${score} out of 10`).length).toBeGreaterThan(0);
  });

  it("shows the current score next to the previous one in the example report", () => {
    render(<HomePage />);

    const example = screen.getByRole("region", { name: "Click through an example report" });
    expect(within(example).getByText(formatRiskScore(SAMPLE_SCORE))).toBeInTheDocument();
    expect(example).toHaveTextContent(`Down from ${formatRiskScore(SAMPLE_PREVIOUS_SCORE)}`);
    expect(within(example).getByText(`Risk score: ${formatRiskScore(SAMPLE_SCORE)} out of 10`)).toBeInTheDocument();
  });

  it("has the anchor targets the header and the app's Help link use", () => {
    const { container } = render(<HomePage />);
    for (const id of ["how-it-works", "checks", "example", "faq"]) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
    }
  });

  it("shows the proof of the finding selected in the example report", async () => {
    const user = userEvent.setup();
    render(<HomePage />);

    const [first, second] = SAMPLE_FINDINGS;
    const tablist = screen.getByRole("tablist", { name: "Fix first" });
    const tabs = within(tablist).getAllByRole("tab");
    expect(tabs).toHaveLength(SAMPLE_FINDINGS.length);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent(first!.proof);

    await user.click(within(tablist).getByRole("tab", { name: new RegExp(second!.plainTitle) }));

    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveTextContent(second!.proof);
    expect(panel).toHaveTextContent(second!.technicalTitle);
  });

  it("opens a FAQ answer from its question button", async () => {
    const user = userEvent.setup();
    render(<HomePage />);

    const faq = screen.getByRole("region", { name: "Questions founders ask" });
    const question = within(faq).getByRole("button", { name: "Do you run my code?" });
    expect(question).toHaveAttribute("aria-expanded", "false");

    await user.click(question);

    expect(question).toHaveAttribute("aria-expanded", "true");
    expect(within(faq).getByText(/never installs your packages/)).toBeVisible();
  });
});

describe("MarketingHeader", () => {
  it("links to the sections and the app, and toggles the mobile menu", async () => {
    const user = userEvent.setup();
    render(<MarketingHeader />);

    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "FAQ" })).toHaveAttribute("href", "#faq");
    expect(within(nav).getByRole("link", { name: "How it works" })).toHaveAttribute("href", "#how-it-works");

    const toggle = screen.getByRole("button", { name: "Open menu" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    const menu = screen.getByRole("navigation", { name: "Sections" });
    expect(within(menu).getByRole("link", { name: "Open app" })).toHaveAttribute("href", "/reports");

    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: "Open menu" })).toHaveAttribute("aria-expanded", "false");
  });

  it("does not show the API status", () => {
    render(<MarketingHeader />);
    expect(screen.getByRole("banner")).not.toHaveTextContent(/API/);
  });
});

describe("MarketingFooter", () => {
  it("says the audit is not a guarantee", () => {
    render(<MarketingFooter />);
    expect(screen.getByRole("contentinfo")).toHaveTextContent(
      "It is not a guarantee that your app is secure.",
    );
  });

  it("does not show the API status", () => {
    render(<MarketingFooter />);
    expect(screen.getByRole("contentinfo")).not.toHaveTextContent(/API/);
  });
});
