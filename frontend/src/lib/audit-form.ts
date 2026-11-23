import { z } from "zod";

/*
  Client-side validation for the new-audit form. It mirrors the backend
  (routers/runs.py + services/runs/code_input.py) so bad input is caught
  before the upload starts; the backend still validates everything.
*/

/** Mirrors the backend's GitHub URL regex: https github.com, owner/repo. */
export const GITHUB_URL_RE = /^https:\/\/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/;

export function isGitHubRepoUrl(value: string): boolean {
  return GITHUB_URL_RE.test(value.trim());
}

/** The API rejects request bodies over 10 MiB; a zip must fit inside that. */
export const MAX_ZIP_BYTES = 10 * 1024 * 1024;

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
    domainToken: z.string().trim(),
  })
  .superRefine((value, ctx) => {
    const hasRepo = value.repoUrl.length > 0;
    const hasZip = value.zipFile !== null;
    if (!hasRepo && !hasZip) {
      ctx.addIssue({
        code: "custom",
        path: ["repoUrl"],
        message: "Add a GitHub repo URL or upload a zip file.",
      });
      ctx.addIssue({
        code: "custom",
        path: ["zipFile"],
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
    if (value.domainToken.length > 1024) {
      ctx.addIssue({
        code: "custom",
        path: ["domainToken"],
        message: "The domain token must be 1024 characters or fewer.",
      });
    }
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
  domainToken: "",
};
