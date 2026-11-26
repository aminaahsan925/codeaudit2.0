import { describe, expect, it } from "vitest";

import { artifactUrl, resolveScreenshotUrl } from "@/lib/artifacts";

import { RUN_ID } from "./fixtures";

describe("artifactUrl", () => {
  it("builds the API artifact URL", () => {
    expect(artifactUrl(RUN_ID, "signup.png")).toBe(
      `http://localhost:8000/api/runs/${RUN_ID}/artifacts/signup.png`,
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

  it("passes an absolute URL through unchanged", () => {
    expect(resolveScreenshotUrl(RUN_ID, "https://cdn.example.com/a.png")).toBe(
      "https://cdn.example.com/a.png",
    );
  });

  it.each([null, undefined, "", "   "])("returns null for %j", (value) => {
    expect(resolveScreenshotUrl(RUN_ID, value)).toBeNull();
  });

  it("rejects path traversal in a bare filename", () => {
    expect(resolveScreenshotUrl(RUN_ID, "../secret.png")).toBeNull();
    expect(resolveScreenshotUrl(RUN_ID, "sub/dir.png")).toBeNull();
  });
});
