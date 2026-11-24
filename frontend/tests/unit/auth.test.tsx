import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthControls } from "@/components/auth-controls";
import { SignInButton } from "@/components/sign-in-button";
import { setSessionToken } from "@/lib/session";

import { renderWithQueryClient } from "./test-utils";

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: replaceMock }),
}));

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubFetch(impl: (req: Request) => Promise<Response>) {
  const fn = vi.fn(impl);
  vi.stubGlobal("fetch", fn);
  return fn;
}

const GOOGLE_USER = {
  subject: "amina@example.com",
  email: "amina@example.com",
  name: "Amina",
  picture_url: "https://example.com/pic.jpg",
  demo: false,
};

const DEMO_USER = {
  subject: "demo@launchaudit.local",
  email: "demo@launchaudit.local",
  name: "Demo User",
  picture_url: null,
  demo: true,
};

beforeEach(() => {
  window.localStorage.clear();
  replaceMock.mockClear();
});

describe("SignInButton", () => {
  it("shows a disabled placeholder while providers load", () => {
    stubFetch(() => new Promise<Response>(() => {}));
    renderWithQueryClient(<SignInButton />);
    const button = screen.getByRole("button", { name: "Sign in" });
    expect(button).toBeDisabled();
  });

  it("shows Sign in with Google when Google is available", async () => {
    stubFetch(async () => json({ google: true, demo: false }));
    renderWithQueryClient(<SignInButton />);
    const link = await screen.findByRole("link", {
      name: "Sign in with Google",
    });
    expect(link).toHaveAttribute(
      "href",
      "http://localhost:8000/api/auth/google/login",
    );
  });

  it("shows the clearly-labelled demo sign-in when Google is not configured", async () => {
    stubFetch(async () => json({ google: false, demo: true }));
    renderWithQueryClient(<SignInButton />);
    expect(
      await screen.findByRole("button", { name: "Demo sign-in" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Demo sign-in: try LaunchAudit without an account/),
    ).toBeInTheDocument();
  });

  it("signs in the demo user and then shows the signed-in state", async () => {
    const fetchMock = stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === "/api/auth/demo-login") {
        return json({
          token: "demo-token",
          demo: true,
          user: {
            id: "00000000-0000-0000-0000-000000000001",
            email: "demo@launchaudit.local",
            name: "Demo User",
            picture_url: null,
            is_demo: true,
          },
        });
      }
      if (path === "/api/auth/me") return json(DEMO_USER);
      return json({ google: false, demo: true });
    });
    renderWithQueryClient(<SignInButton />);
    const button = await screen.findByRole("button", { name: "Demo sign-in" });
    fireEvent.click(button);
    await waitFor(() =>
      expect(
        screen.getByText("Signed in as Demo User (demo account)"),
      ).toBeInTheDocument(),
    );
    expect(
      fetchMock.mock.calls.some(
        (call) =>
          new URL(call[0].url).pathname === "/api/auth/demo-login" &&
          call[0].method === "POST",
      ),
    ).toBe(true);
  });

  it("shows the signed-in user when a session already exists", async () => {
    setSessionToken("session-token-abc");
    stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === "/api/auth/me") return json(GOOGLE_USER);
      return json({ google: true, demo: false });
    });
    renderWithQueryClient(<SignInButton />);
    expect(await screen.findByText("Signed in as Amina")).toBeInTheDocument();
  });

  it("renders nothing when the providers check fails", async () => {
    stubFetch(async () =>
      json(
        { error: { code: "internal_error", message: "Backend is down" } },
        500,
      ),
    );
    const { container } = renderWithQueryClient(<SignInButton />);
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Sign in" }),
      ).not.toBeInTheDocument(),
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe("AuthControls", () => {
  it("shows the signed-in user with picture and a sign-out button", async () => {
    setSessionToken("session-token-abc");
    stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === "/api/auth/me") return json(GOOGLE_USER);
      return json({ google: true, demo: false });
    });
    renderWithQueryClient(<AuthControls />);
    expect(await screen.findByText("Amina")).toBeInTheDocument();
    const avatar = screen.getByText("Amina").closest("div")?.querySelector("img");
    expect(avatar).toHaveAttribute("src", "https://example.com/pic.jpg");
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
  });

  it("labels a demo user as Demo in the header", async () => {
    setSessionToken("demo-token");
    stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === "/api/auth/me") return json(DEMO_USER);
      return json({ google: false, demo: true });
    });
    renderWithQueryClient(<AuthControls />);
    expect(await screen.findByText("Demo User")).toBeInTheDocument();
    expect(screen.getByText("Demo")).toBeInTheDocument();
  });

  it("shows a compact sign-in link when signed out and Google is available", async () => {
    stubFetch(async () => json({ google: true, demo: false }));
    renderWithQueryClient(<AuthControls />);
    const link = await screen.findByRole("link", { name: "Sign in" });
    expect(link).toHaveAttribute(
      "href",
      "http://localhost:8000/api/auth/google/login",
    );
  });

  it("renders nothing when signed out and only demo sign-in is available", async () => {
    stubFetch(async () => json({ google: false, demo: true }));
    const { container } = renderWithQueryClient(<AuthControls />);
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument(),
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("signing out clears the token and goes home", async () => {
    setSessionToken("session-token-abc");
    const fetchMock = stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === "/api/auth/me") return json(GOOGLE_USER);
      if (path === "/api/auth/logout") return json({ signed_out: true });
      return json({ google: true, demo: false });
    });
    renderWithQueryClient(<AuthControls />);
    const button = await screen.findByRole("button", { name: "Sign out" });
    fireEvent.click(button);
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          (call) => new URL(call[0].url).pathname === "/api/auth/logout",
        ),
      ).toBe(true),
    );
    await waitFor(() =>
      expect(window.localStorage.getItem("launchaudit:session:v1")).toBeNull(),
    );
    expect(replaceMock).toHaveBeenCalledWith("/");
  });
});
