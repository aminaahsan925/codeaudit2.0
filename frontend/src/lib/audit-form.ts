import { z } from "zod";

import type { JourneyStepDefinition } from "@/lib/api";

/*
  Client-side validation for the new-audit form. It mirrors the backend
  (routers/runs.py + services/runs/code_input.py + schemas/journey.py) so
  bad input is caught before the upload starts; the backend still
  validates everything.
*/

/** Mirrors the backend's GitHub URL regex: https github.com, owner/repo. */
export const GITHUB_URL_RE = /^https:\/\/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/;

export function isGitHubRepoUrl(value: string): boolean {
  return GITHUB_URL_RE.test(value.trim());
}

/** The API rejects request bodies over 10 MiB; a zip must fit inside that. */
export const MAX_ZIP_BYTES = 10 * 1024 * 1024;

/** Mirrors the backend cap (schemas/journey.py). */
export const MAX_JOURNEY_STEPS = 20;

/** The default journey, shown as read-only info while no custom steps exist. */
export const DEFAULT_JOURNEY_STEPS = ["sign up", "log in", "add to cart", "check out"];

export const JOURNEY_STEP_ACTIONS = ["goto", "fill", "click", "expect_text"] as const;

/** One custom journey step as held in form state (`id` is client-only). */
export const journeyStepFormSchema = z.object({
  id: z.string(),
  action: z.enum(JOURNEY_STEP_ACTIONS),
  url: z.string(),
  selector: z.string(),
  value: z.string(),
  text: z.string(),
  name: z.string(),
});

export type JourneyStepFormValue = z.input<typeof journeyStepFormSchema>;

/** Whether two absolute URLs share an origin (scheme, host and port). */
function isSameOrigin(a: string, b: string): boolean {
  try {
    return new URL(a).origin === new URL(b).origin;
  } catch {
    return false;
  }
}

export const auditFormSchema = z
  .object({
    projectName: z
      .string()
      .trim()
      .min(1, "Enter a project name.")
      .max(200, "Project name must be 200 characters or fewer."),
    repoUrl: z.string().trim(),
    liveUrl: z.string().trim(),
    zipFile: z.instanceof(File).nullable(),
    journeyEmail: z.string().trim(),
    journeyPassword: z.string(),
    journeySteps: z.array(journeyStepFormSchema),
  })
  .superRefine((value, ctx) => {
    const hasRepo = value.repoUrl.length > 0;
    const hasZip = value.zipFile !== null;
    if (!hasRepo && !hasZip) {
      // One issue, on the first field: the message names both options, so
      // showing it under both fields would read as a duplicate.
      ctx.addIssue({
        code: "custom",
        path: ["repoUrl"],
        message: "Add a GitHub repo URL or upload a zip file.",
      });
    }
    if (hasRepo && !isGitHubRepoUrl(value.repoUrl)) {
      ctx.addIssue({
        code: "custom",
        path: ["repoUrl"],
        message: "Enter an https GitHub URL, e.g. https://github.com/owner/repo.",
      });
    }
    if (hasZip && value.zipFile !== null) {
      if (!value.zipFile.name.toLowerCase().endsWith(".zip")) {
        ctx.addIssue({
          code: "custom",
          path: ["zipFile"],
          message: "The uploaded file must be a .zip file.",
        });
      } else if (value.zipFile.size > MAX_ZIP_BYTES) {
        ctx.addIssue({
          code: "custom",
          path: ["zipFile"],
          message: "The zip must be 10 MB or smaller.",
        });
      }
    }
    if (value.liveUrl.length > 0) {
      const parsed = z.url().safeParse(value.liveUrl);
      const url = parsed.success ? new URL(value.liveUrl) : null;
      if (!url || (url.protocol !== "http:" && url.protocol !== "https:")) {
        ctx.addIssue({
          code: "custom",
          path: ["liveUrl"],
          message: "Enter a valid http(s) URL for the live app.",
        });
      } else if (value.liveUrl.length > 2083) {
        ctx.addIssue({
          code: "custom",
          path: ["liveUrl"],
          message: "The live URL must be 2083 characters or fewer.",
        });
      }
    }
    const hasEmail = value.journeyEmail.length > 0;
    const hasPassword = value.journeyPassword.length > 0;
    if (hasEmail !== hasPassword) {
      ctx.addIssue({
        code: "custom",
        path: hasEmail ? ["journeyPassword"] : ["journeyEmail"],
        message: "Provide both a journey email and password, or neither.",
      });
    }
    if (hasEmail && !z.email().safeParse(value.journeyEmail).success) {
      ctx.addIssue({
        code: "custom",
        path: ["journeyEmail"],
        message: "Enter a valid email address.",
      });
    }
    if (value.journeySteps.length > MAX_JOURNEY_STEPS) {
      ctx.addIssue({
        code: "custom",
        path: ["journeySteps"],
        message: `A custom journey has at most ${MAX_JOURNEY_STEPS} steps.`,
      });
    }
    if (value.journeySteps.length > 0 && value.liveUrl.length === 0) {
      ctx.addIssue({
        code: "custom",
        path: ["journeySteps"],
        message: "A custom journey needs a live URL.",
      });
    }
    value.journeySteps.forEach((step, index) => {
      const label = `Step ${index + 1}`;
      const issue = (message: string) =>
        ctx.addIssue({ code: "custom", path: ["journeySteps"], message });
      if (step.name.trim().length > 100) {
        issue(`${label}: the step name must be 100 characters or fewer.`);
      }
      if (step.action === "goto") {
        const url = step.url.trim();
        if (url.length === 0) {
          issue(`${label}: a go-to step needs a URL.`);
        } else if (url.startsWith("//")) {
          issue(`${label}: a go-to URL must not be protocol-relative.`);
        } else if (!url.startsWith("/")) {
          const parsed = z.url().safeParse(url);
          const target = parsed.success ? new URL(url) : null;
          if (
            !target ||
            (target.protocol !== "http:" && target.protocol !== "https:")
          ) {
            issue(`${label}: a go-to URL must be an http(s) URL or a path.`);
          } else if (
            value.liveUrl.length > 0 &&
            !isSameOrigin(url, value.liveUrl)
          ) {
            issue(`${label}: the URL must stay on the live site.`);
          }
        }
      } else if (step.action === "fill") {
        if (step.selector.trim().length === 0) {
          issue(`${label}: a fill step needs a selector.`);
        }
        if (step.value.length === 0) {
          issue(`${label}: a fill step needs a value.`);
        }
      } else if (step.action === "click") {
        if (step.selector.trim().length === 0) {
          issue(`${label}: a click step needs a selector.`);
        }
      } else if (step.text.trim().length === 0) {
        issue(`${label}: an expect-text step needs the text to expect.`);
      }
    });
  });

export type AuditFormValues = z.input<typeof auditFormSchema>;

export type AuditFormErrors = Partial<Record<keyof AuditFormValues, string>>;

/** Validates the form values; returns a field-name to message map, empty when valid. */
export function validateAuditForm(values: AuditFormValues): AuditFormErrors {
  const result = auditFormSchema.safeParse(values);
  if (result.success) return {};
  const errors: AuditFormErrors = {};
  for (const issue of result.error.issues) {
    const field = issue.path[0] as keyof AuditFormValues | undefined;
    if (field && !(field in errors)) errors[field] = issue.message;
  }
  return errors;
}

export const EMPTY_AUDIT_FORM: AuditFormValues = {
  projectName: "",
  repoUrl: "",
  liveUrl: "",
  zipFile: null,
  journeyEmail: "",
  journeyPassword: "",
  journeySteps: [],
};

/**
 * Map form journey steps to the API shape: drop the client-only `id` and
 * any blank fields. Returns undefined when no steps exist, so the run
 * uses the default journey.
 */
export function toJourneyDefinition(
  steps: JourneyStepFormValue[],
): JourneyStepDefinition[] | undefined {
  if (steps.length === 0) return undefined;
  return steps.map((step) => {
    const definition: JourneyStepDefinition = { action: step.action };
    const url = step.url.trim();
    const selector = step.selector.trim();
    const text = step.text.trim();
    const name = step.name.trim();
    if (url) definition.url = url;
    if (selector) definition.selector = selector;
    if (step.value) definition.value = step.value;
    if (text) definition.text = text;
    if (name) definition.name = name;
    return definition;
  });
}
