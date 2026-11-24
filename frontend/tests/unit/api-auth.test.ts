import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  demoLogin,
  getMe,
  getProviders,
  googleLoginUrl,
  logout,
} from "@/lib/api";
import { clearSessionToken, setSessionToken } from "@/lib/session";

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

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => vi.unstubAllGlobals());

describe("auth API helpers", () => {
  it("getProviders calls /api/auth/providers and parses the flags", async () => {
    const fetchMock = stubFetch(async () =>
      json({ google: true, demo: false }),
    );
    await expect(getProviders()).resolves.toEqual({
      google: true,
      demo: false,
    });
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe("/api/auth/providers");
    expect(req.method).toBe("GET");
  });

  it("getMe calls /api/auth/me and parses the user", async () => {
    stubFetch(async () =>
      json({
        subject: "amina@example.com",
        email: "amina@example.com",
        name: "Amina",
        picture_url: null,
        demo: false,
      }),
    );
    await expect(getMe()).resolves.toEqual({
      subject: "amina@example.com",
      email: "amina@example.com",
      name: "Amina",
      picture_url: null,
      demo: false,
    });
  });

  it("demoLogin posts to /api/auth/demo-login and parses the session", async () => {
    const fetchMock = stubFetch(async () =>
      json({
        token: "demo-token",
        demo: true,
        user: {
          id: "00000000-0000-0000-0000-000000000001",
          email: "demo@launchaudit.local",
          name: "Demo User",
          picture_url: null,
          is_demo: true,
        },
      }),
    );
    const session = await demoLogin();
    expect(session.token).toBe("demo-token");
    expect(session.demo).toBe(true);
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe("/api/auth/demo-login");
    expect(req.method).toBe("POST");
  });

  it("logout posts to /api/auth/logout", async () => {
    const fetchMock = stubFetch(async () => json({ signed_out: true }));
    await expect(logout()).resolves.toBeUndefined();
    const req = fetchMock.mock.calls[0]![0];
    expect(new URL(req.url).pathname).toBe("/api/auth/logout");
    expect(req.method).toBe("POST");
  });

  it("googleLoginUrl points at the backend login redirect", () => {
    expect(googleLoginUrl()).toBe(
      "http://localhost:8000/api/auth/google/login",
    );
  });
});

describe("session token on API calls", () => {
  it("sends the stored token as a Bearer header", async () => {
    setSessionToken("session-token-abc");
    const fetchMock = stubFetch(async () =>
      json({ subject: "dev", email: null, name: null, picture_url: null, demo: false }),
    );
    await getMe();
    const req = fetchMock.mock.calls[0]![0];
    expect(req.headers.get("Authorization")).toBe("Bearer session-token-abc");
  });

  it("sends no Authorization header when signed out", async () => {
    const fetchMock = stubFetch(async () =>
      json({ google: false, demo: true }),
    );
    await getProviders();
    const req = fetchMock.mock.calls[0]![0];
    expect(req.headers.get("Authorization")).toBeNull();
  });

  it("stops sending the header after the token is cleared", async () => {
    setSessionToken("session-token-abc");
    clearSessionToken();
    const fetchMock = stubFetch(async () =>
      json({ google: false, demo: true }),
    );
    await getProviders();
    const req = fetchMock.mock.calls[0]![0];
    expect(req.headers.get("Authorization")).toBeNull();
  });
});
