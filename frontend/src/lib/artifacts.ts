import { env } from "@/lib/env";

/**
 * URL of a run artifact (screenshot or PDF) served by the API. Artifacts
 * are public by run id; the name must be a bare filename.
 */
export function artifactUrl(runId: string, name: string): string {
  return (
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/runs/${encodeURIComponent(runId)}` +
    `/artifacts/${encodeURIComponent(name)}`
  );
}

/**
 * Resolves a screenshot reference from the API into a loadable URL.
 *
 * The API is inconsistent about the shape: finding evidence carries a
 * relative path (`/api/runs/{id}/artifacts/{name}.png`), while journey
 * steps carry a bare filename (`signup.png`). Absolute URLs pass through
 * unchanged. Returns null for an empty or unsafe value.
 */
export function resolveScreenshotUrl(
  runId: string,
  value: string | null | undefined,
): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (trimmed.startsWith("/api/runs/")) {
    return `${env.NEXT_PUBLIC_API_BASE_URL}${trimmed}`;
  }
  if (trimmed.includes("/") || trimmed.includes("\\") || trimmed.includes("..")) {
    return null;
  }
  return artifactUrl(runId, trimmed);
}
