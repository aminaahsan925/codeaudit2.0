import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Markdown } from "@/components/markdown";

describe("Markdown", () => {
  it("renders headings, paragraphs, bold and inline code", () => {
    render(
      <Markdown
        text={
          "## Why it matters\n\nA leaked key lets **strangers** read your data.\n\n" +
          "## How to fix\n\nMove it to `process.env` and rotate it."
        }
      />,
    );
    expect(screen.getByRole("heading", { name: "Why it matters" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "How to fix" })).toBeVisible();
    expect(screen.getByText("strangers")).toBeVisible();
    expect(screen.getByText("process.env").tagName).toBe("CODE");
  });

  it("renders lists and fenced code blocks", () => {
    render(
      <Markdown
        text={
          "- Rotate the key\n- Remove it from history\n\n" +
          "```\nconst key = process.env.API_KEY;\n```"
        }
      />,
    );
    expect(screen.getByRole("list")).toBeVisible();
    expect(screen.getByText("Rotate the key")).toBeVisible();
    expect(screen.getByText("const key = process.env.API_KEY;")).toBeVisible();
  });

  it("renders nothing for empty text", () => {
    const { container } = render(<Markdown text={"  \n\n  "} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("does not inject markup from the text", () => {
    render(<Markdown text={"Fix the <script>alert(1)</script> issue."} />);
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText(/Fix the/)).toHaveTextContent(
      "Fix the <script>alert(1)</script> issue.",
    );
  });
});
