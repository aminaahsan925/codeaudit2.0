import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ShareLink } from "@/components/share-link";

describe("ShareLink", () => {
  it("shows the full share URL", () => {
    render(<ShareLink path="/r/abc-123" />);
    const input = screen.getByLabelText("Share link") as HTMLInputElement;
    expect(input.value).toBe("http://localhost:3000/r/abc-123");
    expect(input.readOnly).toBe(true);
  });

  it("copies the link and confirms", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    render(<ShareLink path="/r/abc-123" />);
    await user.click(screen.getByRole("button", { name: "Copy link" }));

    expect(writeText).toHaveBeenCalledWith("http://localhost:3000/r/abc-123");
    expect(screen.getByRole("button", { name: "Copied" })).toBeVisible();
    expect(screen.getByText("Share link copied to the clipboard.")).toBeInTheDocument();
  });
});
