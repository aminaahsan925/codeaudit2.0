import { describe, expect, it } from "vitest";

import { artifactUrl, resolveScreenshotUrl } from "@/lib/artifacts";

import { RUN_ID } from "./fixtures";

const SHARE_TOKEN = "share-token-1";

/** The artifact URL with the share token appended as a query param. */
function artifactUrlWithToken(name: string): string {
  const base = `http://localhost:8000/api/runs/${RUN_ID}/artifacts/${name}`;
  return `${base}?${new URLSearchParams({ token: SHARE_TOKEN }).toString()}`;
}

describe("artifactUrl", () => {
  it("builds the API artifact URL", () => {
    expect(artifactUrl(RUN_ID, "signup.png")).toBe(
      `http://localhost:8000/api/runs/${RUN_ID}/artifacts/signup.png`,
    );
  });

  it("appends the share token when one is given", () => {
    expect(artifactUrl(RUN_ID, "signup.png", SHARE_TOKEN)).toBe(
      artifactUrlWithToken("signup.png"),
    );
  });
});

describe("resolveScreenshotUrl", () => {
  it("resolves a bare filename against the run's artifacts", () => {
    expect(resolveScreenshotUrl(RUN_ID, "signup.png")).toBe(
      `http://localhost:8000/api/runs/${RUN_ID}/artifacts/signup.png`,
    );
  });

  it("resolves a relative API path against the API origin", () => {
    expect(
      resolveScreenshotUrl(RUN_ID, `/api/runs/${RUN_ID}/artifacts/checkout.png`),
    ).toBe(`http://localhost:8000/api/runs/${RUN_ID}/artifacts/checkout.png`);
  });

  it("passes an absolute URL through unchanged, even with a share token", () => {
    expect(
      resolveScreenshotUrl(RUN_ID, "https://cdn.example.com/a.png", SHARE_TOKEN),
    ).toBe("https://cdn.example.com/a.png");
  });

  it("appends the share token to a relative API path", () => {
    expect(
      resolveScreenshotUrl(
        RUN_ID,
        `/api/runs/${RUN_ID}/artifacts/checkout.png`,
        SHARE_TOKEN,
      ),
    ).toBe(artifactUrlWithToken("checkout.png"));
  });

  it.each([null, undefined, "", "   "])("returns null for %j", (value) => {
    expect(resolveScreenshotUrl(RUN_ID, value)).toBeNull();
  });

  it("rejects path traversal in a bare filename", () => {
    expect(resolveScreenshotUrl(RUN_ID, "../secret.png")).toBeNull();
    expect(resolveScreenshotUrl(RUN_ID, "sub/dir.png")).toBeNull();
  });
});
