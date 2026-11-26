import { describe, expect, it } from "vitest";

import { RULE_TITLES, plainTitleFor } from "@/lib/finding-titles";

const base = { category: "other", engine: "native", title: "x" } as const;

describe("plainTitleFor", () => {
  it("returns the mapped title for every known rule id", () => {
    for (const [id, title] of Object.entries(RULE_TITLES)) {
      expect(plainTitleFor({ ...base, rule_id: id })).toBe(title);
    }
  });

  it("keeps every title short and free of dashes used as punctuation", () => {
    for (const title of Object.values(RULE_TITLES)) {
      expect(title.length).toBeLessThanOrEqual(70);
      expect(title).not.toMatch(/[—–]/);
    }
  });

  it("maps external engines by pattern", () => {
    expect(
      plainTitleFor({ ...base, rule_id: "generic-api-key", engine: "gitleaks", category: "secrets" }),
    ).toBe("A secret key is exposed in your code");
    expect(
      plainTitleFor({ ...base, rule_id: "GHSA-1234", engine: "osv", category: "dependency" }),
    ).toBe("A library you use has a known security bug");
  });

  it("falls back by category for unknown ids", () => {
    const title = plainTitleFor({ ...base, rule_id: "semgrep:foo.bar", engine: "semgrep", category: "xss" });
    expect(title).toBe("Someone can run their own script in your users' browsers");
    expect(plainTitleFor({ ...base, rule_id: "NOPE" })).not.toMatch(/[—–]/);
  });
});
