"use client";

import { Search } from "lucide-react";
import { Suspense, useEffect, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

import { Breadcrumbs } from "./breadcrumbs";
import { Kbd } from "./kbd";
import { MobileNav } from "./mobile-nav";
import { AuthControls } from "@/components/auth-controls";
import { useModifierLabel, useShell } from "./shell-context";

function SearchButton() {
  const { setPaletteOpen } = useShell();
  const mod = useModifierLabel();

  return (
    <button
      type="button"
      onClick={() => setPaletteOpen(true)}
      aria-haspopup="dialog"
      aria-keyshortcuts="Control+K Meta+K /"
      className={cn(
        "inline-flex size-9 items-center justify-center gap-2 rounded-[10px] text-sm text-muted-foreground transition-colors hover:bg-sunken hover:text-foreground",
        "md:w-56 md:justify-start md:border md:border-border md:bg-card md:pr-1.5 md:pl-3 md:shadow-xs md:hover:border-input md:hover:bg-card",
      )}
    >
      <Search aria-hidden="true" className="size-4 shrink-0" />
      <span className="sr-only md:not-sr-only">Search</span>
      <span aria-hidden="true" className="ml-auto hidden items-center gap-1 md:inline-flex">
        <Kbd>{mod}</Kbd>
        <Kbd>K</Kbd>
      </span>
    </button>
  );
}

/** True once the page has scrolled past the top bar's own height. */
function useScrolled(threshold = 4): boolean {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const update = () => setScrolled(window.scrollY > threshold);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, [threshold]);
  return scrolled;
}

export function TopBar() {
  const scrolled = useScrolled();

  return (
    <header
      data-scrolled={scrolled ? "" : undefined}
      className={cn(
        "sticky top-0 z-30 border-b transition-[background-color,border-color] duration-200",
        scrolled ? "bar-solid border-border" : "border-transparent bg-background",
      )}
    >
      <div className="container-page flex h-14 items-center gap-2">
        <MobileNav className="-ml-2 lg:hidden" />
        {/*
          Breadcrumbs read the pathname, which is request data on dynamic
          routes with cacheComponents; the fallback holds the row's height.
        */}
        <Suspense fallback={<div aria-hidden="true" className="h-9 min-w-0 flex-1" />}>
          <Breadcrumbs className="min-w-0 flex-1" />
        </Suspense>
        <div className="ml-auto flex shrink-0 items-center gap-1 sm:gap-1.5">
          <SearchButton />
          <ThemeToggle />
          <AuthControls />
        </div>
      </div>
    </header>
  );
}
