import { env } from "@/lib/env";

/** Appends the share token as a query param, or returns the URL unchanged. */
function withShareToken(url: string, shareToken?: string): string {
  if (!shareToken) return url;
  const query = new URLSearchParams({ token: shareToken }).toString();
  return `${url}?${query}`;
}

/**
 * URL of a run artifact (screenshot or PDF) served by the API. Artifacts
 * need the run's owner or a share token; plain img tags carry no bearer
 * token, so callers pass the run's share token when the report has one.
 * The name must be a bare filename.
 */
export function artifactUrl(
  runId: string,
  name: string,
  shareToken?: string,
): string {
  return withShareToken(
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/runs/${encodeURIComponent(runId)}` +
      `/artifacts/${encodeURIComponent(name)}`,
    shareToken,
  );
}

/**
 * Resolves a screenshot reference from the API into a loadable URL.
 *
 * The API is inconsistent about the shape: finding evidence carries a
 * relative path (`/api/runs/{id}/artifacts/{name}.png`), while journey
 * steps carry a bare filename (`signup.png`). Absolute URLs pass through
 * unchanged (and never get a share token). Returns null for an empty or
 * unsafe value.
 */
export function resolveScreenshotUrl(
  runId: string,
  value: string | null | undefined,
  shareToken?: string,
): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (trimmed.startsWith("/api/runs/")) {
    return withShareToken(`${env.NEXT_PUBLIC_API_BASE_URL}${trimmed}`, shareToken);
  }
  if (trimmed.includes("/") || trimmed.includes("\\") || trimmed.includes("..")) {
    return null;
  }
  return artifactUrl(runId, trimmed, shareToken);
}
