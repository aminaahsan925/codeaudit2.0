import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { HealthBadge } from "@/components/health-badge";
import { useHealth } from "@/hooks/use-health";
import { ApiError } from "@/lib/api";

vi.mock("@/hooks/use-health", () => ({ useHealth: vi.fn() }));

type HookResult = ReturnType<typeof useHealth>;

function mockHook(partial: Record<string, unknown>) {
  const refetch = vi.fn().mockResolvedValue({});
  vi.mocked(useHealth).mockReturnValue({
    status: "pending",
    data: undefined,
    error: null,
    isFetching: false,
    refetch,
    ...partial,
  } as unknown as HookResult);
  return refetch;
}

describe("HealthBadge", () => {
  it("shows a checking state while loading", () => {
    mockHook({ status: "pending", isFetching: true });
    render(<HealthBadge />);
    expect(screen.getByRole("button", { name: "Checking API" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("LaunchAudit Checking API");
    expect(screen.getByText("Contacting the LaunchAudit API.")).toBeInTheDocument();
  });

  it("shows online with the version", () => {
    mockHook({ status: "success", data: { status: "ok", version: "0.1.0" } });
    render(<HealthBadge />);
    const button = screen.getByRole("button", { name: "API online" });
    expect(button).toHaveAccessibleDescription(
      "Version 0.1.0. Checked every 30 seconds.",
    );
    expect(screen.getByRole("status")).toHaveTextContent("LaunchAudit API online");
  });

  it("shows offline with the error message", () => {
    mockHook({
      status: "error",
      error: new ApiError("network_error", "Could not reach the LaunchAudit API."),
    });
    render(<HealthBadge />);
    const button = screen.getByRole("button", { name: "API offline" });
    expect(button).toHaveAccessibleDescription("Could not reach the LaunchAudit API.");
    expect(screen.getByRole("status")).toHaveTextContent("LaunchAudit API offline");
  });

  it("falls back to a generic offline message", () => {
    mockHook({ status: "error", error: null });
    render(<HealthBadge />);
    expect(screen.getByRole("button", { name: "API offline" })).toHaveAccessibleDescription(
      "The API is not responding.",
    );
  });

  it("announces politely through a status region", () => {
    mockHook({ status: "success", data: { status: "ok", version: "1.0.0" } });
    render(<HealthBadge />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("re-checks when clicked", async () => {
    const refetch = mockHook({
      status: "error",
      error: new ApiError("timeout", "Too slow"),
    });
    render(<HealthBadge />);
    await userEvent.setup().click(screen.getByRole("button", { name: "API offline" }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("does not start another check while one is in flight", async () => {
    const refetch = mockHook({
      status: "success",
      data: { status: "ok", version: "1" },
      isFetching: true,
    });
    render(<HealthBadge />);
    await userEvent.setup().click(screen.getByRole("button", { name: "API online" }));
    expect(refetch).not.toHaveBeenCalled();
  });
});
