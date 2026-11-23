import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

async function loadEnv() {
  vi.resetModules();
  return import("@/lib/env");
}

beforeEach(() => {
  vi.unstubAllEnvs();
});
afterEach(() => {
  vi.unstubAllEnvs();
});

describe("env", () => {
  it("accepts a valid URL and strips trailing slashes", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com//");
    const { env, apiOrigin } = await loadEnv();
    expect(env.NEXT_PUBLIC_API_BASE_URL).toBe("https://api.example.com");
    expect(apiOrigin).toBe("https://api.example.com");
  });

  it("strips a trailing slash after a path; origin has no path", async () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:9000/v1/");
    const { env, apiOrigin } = await loadEnv();
    expect(env.NEXT_PUBLIC_API_BASE_URL).toBe("http://localhost:9000/v1");
    expect(apiOrigin).toBe("http://localhost:9000");
  });

  it("defaults to localhost:8000 outside production", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    const { env, isDevelopment, isProduction } = await loadEnv();
    expect(env.NEXT_PUBLIC_API_BASE_URL).toBe("http://localhost:8000");
    expect(isDevelopment).toBe(true);
    expect(isProduction).toBe(false);
  });

  it.each(["not a url", "ftp://example.com", "javascript:alert(1)", "/relative"])(
    "rejects invalid URL %s naming the variable",
    async (value) => {
      vi.stubEnv("NODE_ENV", "development");
      vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", value);
      await expect(loadEnv()).rejects.toThrow(/NEXT_PUBLIC_API_BASE_URL/);
    },
  );

  it("fails in production when NEXT_PUBLIC_API_BASE_URL is missing", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    await expect(loadEnv()).rejects.toThrow(
      /NEXT_PUBLIC_API_BASE_URL is required in production/,
    );
  });

  it("accepts production with the variable set", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com");
    const { env, isProduction } = await loadEnv();
    expect(env.NODE_ENV).toBe("production");
    expect(isProduction).toBe(true);
  });

  it("rejects an unknown NODE_ENV", async () => {
    vi.stubEnv("NODE_ENV", "staging");
    await expect(loadEnv()).rejects.toThrow(/NODE_ENV/);
  });
});
