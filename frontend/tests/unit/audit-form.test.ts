import { describe, expect, it } from "vitest";

import {
  EMPTY_AUDIT_FORM,
  isGitHubRepoUrl,
  toJourneyDefinition,
  validateAuditForm,
  type AuditFormValues,
  type JourneyStepFormValue,
} from "@/lib/audit-form";

function values(overrides: Partial<AuditFormValues> = {}): AuditFormValues {
  return { ...EMPTY_AUDIT_FORM, ...overrides };
}

function step(overrides: Partial<JourneyStepFormValue> = {}): JourneyStepFormValue {
  return {
    id: "step-1",
    action: "goto",
    url: "/reset",
    selector: "",
    value: "",
    text: "",
    name: "",
    ...overrides,
  };
}

const zip = (name = "app.zip", size = 1024) =>
  new File([new Uint8Array(size)], name, { type: "application/zip" });

describe("isGitHubRepoUrl", () => {
  it.each([
    "https://github.com/owner/repo",
    "https://github.com/owner/repo.git",
    "https://github.com/owner/repo/",
    "https://github.com/my-org/my.repo-name_1",
  ])("accepts %s", (url) => {
    expect(isGitHubRepoUrl(url)).toBe(true);
  });

  it.each([
    "http://github.com/owner/repo",
    "https://gitlab.com/owner/repo",
    "https://github.com/owner",
    "https://github.com/owner/repo/tree/main",
    "https://user:pass@github.com/owner/repo",
    "github.com/owner/repo",
    "",
  ])("rejects %s", (url) => {
    expect(isGitHubRepoUrl(url)).toBe(false);
  });
});

describe("validateAuditForm", () => {
  it("accepts a repo URL run", () => {
    expect(
      validateAuditForm(
        values({
          projectName: "pocket-notes",
          repoUrl: "https://github.com/example/pocket-notes",
        }),
      ),
    ).toEqual({});
  });

  it("accepts a zip run", () => {
    expect(
      validateAuditForm(values({ projectName: "pocket-notes", zipFile: zip() })),
    ).toEqual({});
  });

  it("requires a project name", () => {
    const errors = validateAuditForm(
      values({ repoUrl: "https://github.com/example/pocket-notes" }),
    );
    expect(errors.projectName).toBe("Enter a project name.");
  });

  it("requires a repo URL or a zip", () => {
    const errors = validateAuditForm(values({ projectName: "pocket-notes" }));
    expect(errors.repoUrl).toBe("Add a GitHub repo URL or upload a zip file.");
    // Shown once, under the repo field: the message names both options.
    expect(errors.zipFile).toBeUndefined();
  });

  it("rejects a non-GitHub repo URL", () => {
    const errors = validateAuditForm(
      values({ projectName: "x", repoUrl: "https://gitlab.com/a/b" }),
    );
    expect(errors.repoUrl).toMatch(/https GitHub URL/);
  });

  it("rejects a non-zip upload", () => {
    const errors = validateAuditForm(
      values({ projectName: "x", zipFile: zip("app.tar.gz") }),
    );
    expect(errors.zipFile).toBe("The uploaded file must be a .zip file.");
  });

  it("rejects a zip over 10 MB", () => {
    const errors = validateAuditForm(
      values({ projectName: "x", zipFile: zip("app.zip", 10 * 1024 * 1024 + 1) }),
    );
    expect(errors.zipFile).toBe("The zip must be 10 MB or smaller.");
  });

  it("rejects a malformed live URL", () => {
    const errors = validateAuditForm(
      values({
        projectName: "x",
        repoUrl: "https://github.com/a/b",
        liveUrl: "not a url",
      }),
    );
    expect(errors.liveUrl).toBe("Enter a valid http(s) URL for the live app.");
  });

  it("requires journey credentials as a pair", () => {
    const errors = validateAuditForm(
      values({
        projectName: "x",
        repoUrl: "https://github.com/a/b",
        journeyEmail: "tester@example.com",
      }),
    );
    expect(errors.journeyPassword).toBe(
      "Provide both a journey email and password, or neither.",
    );
  });

  it("rejects a malformed journey email", () => {
    const errors = validateAuditForm(
      values({
        projectName: "x",
        repoUrl: "https://github.com/a/b",
        journeyEmail: "not-an-email",
        journeyPassword: "secret",
      }),
    );
    expect(errors.journeyEmail).toBe("Enter a valid email address.");
  });

  it("accepts a valid custom journey", () => {
    expect(
      validateAuditForm(
        values({
          projectName: "pocket-notes",
          repoUrl: "https://github.com/example/pocket-notes",
          liveUrl: "https://shop.example.com",
          journeySteps: [
            step(),
            step({
              id: "step-2",
              action: "fill",
              url: "",
              selector: "#email",
              value: "user@example.com",
            }),
            step({ id: "step-3", action: "click", url: "", selector: "button" }),
            step({ id: "step-4", action: "expect_text", url: "", text: "Done" }),
          ],
        }),
      ),
    ).toEqual({});
  });

  it("rejects a custom journey without a live URL", () => {
    const errors = validateAuditForm(
      values({
        projectName: "x",
        repoUrl: "https://github.com/a/b",
        journeySteps: [step()],
      }),
    );
    expect(errors.journeySteps).toBe("A custom journey needs a live URL.");
  });

  it("rejects a fill step without a selector", () => {
    const errors = validateAuditForm(
      values({
        projectName: "x",
        repoUrl: "https://github.com/a/b",
        liveUrl: "https://shop.example.com",
        journeySteps: [
          step(),
          step({ id: "step-2", action: "fill", url: "", value: "user@example.com" }),
        ],
      }),
    );
    expect(errors.journeySteps).toBe("Step 2: a fill step needs a selector.");
  });

  it("rejects an off-origin go-to URL", () => {
    const errors = validateAuditForm(
      values({
        projectName: "x",
        repoUrl: "https://github.com/a/b",
        liveUrl: "https://shop.example.com",
        journeySteps: [step({ url: "https://other.example.com/" })],
      }),
    );
    expect(errors.journeySteps).toBe("Step 1: the URL must stay on the live site.");
  });

  it("rejects more than 20 journey steps", () => {
    const errors = validateAuditForm(
      values({
        projectName: "x",
        repoUrl: "https://github.com/a/b",
        liveUrl: "https://shop.example.com",
        journeySteps: Array.from({ length: 21 }, (_, i) =>
          step({ id: `step-${i}` }),
        ),
      }),
    );
    expect(errors.journeySteps).toBe("A custom journey has at most 20 steps.");
  });
});

describe("toJourneyDefinition", () => {
  it("returns undefined for an empty journey", () => {
    expect(toJourneyDefinition([])).toBeUndefined();
  });

  it("drops the client id and blank fields", () => {
    expect(
      toJourneyDefinition([
        step({ name: "Open reset" }),
        step({
          id: "step-2",
          action: "fill",
          url: "",
          selector: "  #email  ",
          value: "user@example.com",
        }),
      ]),
    ).toEqual([
      { action: "goto", url: "/reset", name: "Open reset" },
      { action: "fill", selector: "#email", value: "user@example.com" },
    ]);
  });
});
