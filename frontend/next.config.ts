import type { NextConfig } from "next";

import { apiOrigin, isDevelopment, isProduction } from "./src/lib/env";

/*
  Content Security Policy

  - script-src 'unsafe-inline': the App Router streams its RSC payload as
    inline <script> tags, and next-themes adds a small inline script that sets
    the theme class before first paint (no flash). Removing it requires a
    per-request nonce from proxy.ts, which forces every page to render
    dynamically. Revisit once pages are dynamic anyway.
  - script-src 'unsafe-eval': development only. React uses eval to rebuild
    server error stacks in the browser; production never needs it.
  - style-src 'unsafe-inline': Next.js and next/font inject inline <style>
    tags and components set inline style attributes.
  - connect-src: this origin plus the LaunchAudit API origin from env.ts.
*/
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDevelopment ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  // Journey and finding screenshots are served by the API origin.
  `img-src 'self' data: blob: ${apiOrigin}`,
  "font-src 'self'",
  `connect-src 'self' ${apiOrigin}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "manifest-src 'self'",
  "worker-src 'self' blob:",
  // Skipped when the API itself is plain http (local production smoke tests).
  ...(isProduction && apiOrigin.startsWith("https:") ? ["upgrade-insecure-requests"] : []),
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value:
      "camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()",
  },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  ...(isProduction
    ? [
        {
          key: "Strict-Transport-Security",
          value: "max-age=63072000; includeSubDomains",
        },
      ]
    : []),
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // The dev-only indicator sits bottom-right so it never covers the sidebar's
  // API status chip (bottom-left). Production builds never show it.
  devIndicators: { position: "bottom-right" },
  reactStrictMode: true,
  // Stop `next dev` from writing generated guidance files into the repo.
  agentRules: false,
  typescript: {
    // Production build type-checks app code only; tests are covered by pnpm typecheck.
    tsconfigPath: "tsconfig.build.json",
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
