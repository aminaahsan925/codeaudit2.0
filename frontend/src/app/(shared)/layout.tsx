import type { ReactNode } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Wordmark } from "@/components/wordmark";

/**
 * Minimal chrome for reports shared by link. The reader has no account and no
 * use for app navigation; the report's own action bar offers "Run your own
 * audit".
 */
export default function SharedLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-border bg-background">
        <div className="container-page flex h-16 items-center gap-3">
          <Wordmark />
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main id="main" tabIndex={-1} className="flex flex-1 flex-col outline-none">
        {children}
      </main>
      <footer className="border-t border-border">
        <p className="container-page py-6 text-sm text-muted-foreground">
          LaunchAudit finds common security problems. It is not a guarantee that an app is secure.
        </p>
      </footer>
    </div>
  );
}
