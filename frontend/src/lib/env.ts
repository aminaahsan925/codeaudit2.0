import { z } from "zod";

/*
  The only module that reads process.env (enforced by ESLint).

  Every key is referenced literally so Next.js can inline NEXT_PUBLIC_*
  values into the browser bundle. Anything prefixed NEXT_PUBLIC_ is public:
  never put secrets here.
*/

const DEV_API_BASE_URL = "http://localhost:8000";

const nodeEnvSchema = z
  .enum(["development", "test", "production"])
  .default("development");

const apiBaseUrlSchema = z
  .url({
    protocol: /^https?$/,
    error: "must be an absolute http(s) URL, e.g. https://api.example.com",
  })
  .transform((value) => value.replace(/\/+$/, ""));

function blankToUndefined(value: string | undefined): string | undefined {
  return value === undefined || value.trim() === "" ? undefined : value.trim();
}

export class EnvError extends Error {
  override name = "EnvError";
}

export interface Env {
  NODE_ENV: "development" | "test" | "production";
  NEXT_PUBLIC_API_BASE_URL: string;
}

export function parseEnv(raw: Record<string, string | undefined>): Env {
  const nodeEnv = nodeEnvSchema.safeParse(blankToUndefined(raw.NODE_ENV));
  if (!nodeEnv.success) {
    throw new EnvError(
      "Invalid environment: NODE_ENV must be development, test or production.",
    );
  }

  const rawApiBaseUrl = blankToUndefined(raw.NEXT_PUBLIC_API_BASE_URL);
  if (rawApiBaseUrl === undefined && nodeEnv.data === "production") {
    throw new EnvError(
      "Invalid environment: NEXT_PUBLIC_API_BASE_URL is required in production " +
        "(the public origin of the LaunchAudit API, e.g. https://api.example.com).",
    );
  }

  const apiBaseUrl = apiBaseUrlSchema.safeParse(
    rawApiBaseUrl ?? DEV_API_BASE_URL,
  );
  if (!apiBaseUrl.success) {
    const reason = apiBaseUrl.error.issues[0]?.message ?? "is invalid";
    throw new EnvError(
      `Invalid environment: NEXT_PUBLIC_API_BASE_URL ${reason}.`,
    );
  }

  return {
    NODE_ENV: nodeEnv.data,
    NEXT_PUBLIC_API_BASE_URL: apiBaseUrl.data,
  };
}

export const env: Env = parseEnv({
  NODE_ENV: process.env.NODE_ENV,
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
});

export const isDevelopment = env.NODE_ENV === "development";
export const isProduction = env.NODE_ENV === "production";

/** Origin of the API (scheme + host + port), used for CSP connect-src. */
export const apiOrigin = new URL(env.NEXT_PUBLIC_API_BASE_URL).origin;
