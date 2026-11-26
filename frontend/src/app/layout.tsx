import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, IBM_Plex_Mono, Instrument_Sans } from "next/font/google";
import type { ReactNode } from "react";

import { Providers } from "./providers";
import "./globals.css";

const display = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  weight: ["500", "600"],
  display: "swap",
});

const sans = Instrument_Sans({
  variable: "--font-instrument",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const mono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "LaunchAudit: find out if your app is safe to launch",
    template: "%s | LaunchAudit",
  },
  description:
    "LaunchAudit checks apps built with AI tools before launch. Add your code and live site to get a verdict, a 0-10 risk score and the proof behind every problem.",
  applicationName: "LaunchAudit",
  referrer: "strict-origin-when-cross-origin",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f5f2" },
    { media: "(prefers-color-scheme: dark)", color: "#0f0e15" },
  ],
};

// Explicit props instead of Next's generated `LayoutProps` global, so
// `pnpm typecheck` works on a fresh checkout before any build has run.
// The marketing page and the app pages each bring their own chrome from
// their route group layout: (marketing) and (app).
export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${display.variable} ${sans.variable} ${mono.variable}`}
    >
      <body className="min-h-dvh">
        <Providers>
          <a
            href="#main"
            className="fixed top-2 left-2 z-[70] -translate-y-20 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground focus:translate-y-0"
          >
            Skip to content
          </a>
          {children}
        </Providers>
      </body>
    </html>
  );
}
