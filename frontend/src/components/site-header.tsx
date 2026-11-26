import { Suspense } from "react";

import { HealthBadge } from "@/components/health-badge";
import { MainNav } from "@/components/main-nav";
import { MobileNav } from "@/components/mobile-nav";
import { ThemeToggle } from "@/components/theme-toggle";
import { Wordmark } from "@/components/wordmark";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background">
      <div className="container-page flex h-16 items-center gap-3 md:gap-8">
        <Wordmark />
        {/*
          Both navs read the pathname to mark the current page. With
          cacheComponents, that value is only known at request time on
          dynamic routes, so the navs stream in behind Suspense; the
          fallbacks hold their space to avoid a layout shift.
        */}
        <Suspense
          fallback={
            <div aria-hidden="true" className="hidden h-9 w-52 md:block" />
          }
        >
          <MainNav className="hidden md:block" />
        </Suspense>
        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <HealthBadge />
          <ThemeToggle />
          <Suspense
            fallback={<div aria-hidden="true" className="size-9 md:hidden" />}
          >
            <MobileNav className="md:hidden" />
          </Suspense>
        </div>
      </div>
    </header>
  );
}
