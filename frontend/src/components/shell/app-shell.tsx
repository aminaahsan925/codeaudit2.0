import type { ReactNode } from "react";

import { LazyCommandPalette } from "./lazy-command-palette";
import { ShellProvider } from "./shell-context";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";

/**
 * The app chrome: sidebar (drawer below 1024px), top bar, main region and
 * command palette. Pages bring their own `container-page` width and padding.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <ShellProvider>
      <div className="flex min-h-dvh">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main id="main" tabIndex={-1} className="flex flex-1 flex-col outline-none">
            {children}
          </main>
        </div>
      </div>
      <LazyCommandPalette />
    </ShellProvider>
  );
}
