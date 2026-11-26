"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useId, useRef, useState, useSyncExternalStore } from "react";

import { ButtonLink } from "@/components/button-link";
import { ThemeToggle } from "@/components/theme-toggle";
import { Wordmark } from "@/components/wordmark";

const SECTIONS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#checks", label: "Checks" },
  { href: "#faq", label: "FAQ" },
] as const;

/** Passive scroll listener, at most one check per animation frame. */
function subscribeScroll(onChange: () => void) {
  let frame = 0;
  function onScroll() {
    if (frame) return;
    frame = window.requestAnimationFrame(() => {
      frame = 0;
      onChange();
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  return () => {
    window.removeEventListener("scroll", onScroll);
    if (frame) window.cancelAnimationFrame(frame);
  };
}

/** True once the page has scrolled, which turns on its solid background and border. */
function useScrolled(): boolean {
  return useSyncExternalStore(
    subscribeScroll,
    () => window.scrollY > 8,
    () => false,
  );
}

export function MarketingHeader() {
  const scrolled = useScrolled();
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header
      data-scrolled={scrolled || open}
      className="sticky top-0 z-30 border-b border-transparent transition-[background-color,border-color] duration-200 data-[scrolled=true]:bar-solid data-[scrolled=true]:border-border/80"
    >
      <div className="container-page flex h-16 items-center gap-6">
        <Wordmark />
        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {SECTIONS.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  className="inline-flex h-9 items-center rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <ButtonLink href="/reports" variant="ghost" className="hidden sm:inline-flex">
            Open app
          </ButtonLink>
          <ButtonLink href="/audits/new" className="hidden sm:inline-flex">
            Run an audit
          </ButtonLink>
          <button
            ref={buttonRef}
            type="button"
            aria-expanded={open}
            aria-controls={menuId}
            onClick={() => setOpen((value) => !value)}
            className="inline-flex size-9 items-center justify-center rounded-lg hover:bg-muted md:hidden"
          >
            {open ? <X aria-hidden="true" className="size-5" /> : <Menu aria-hidden="true" className="size-5" />}
            <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
          </button>
        </div>
      </div>
      <div
        id={menuId}
        hidden={!open}
        className="border-t bg-card shadow-float md:hidden"
      >
        <nav aria-label="Sections" className="container-page py-3">
          <ul className="flex flex-col">
            {SECTIONS.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className="flex h-12 items-center rounded-lg px-2 text-base font-medium hover:bg-muted"
                >
                  {item.label}
                </a>
              </li>
            ))}
            <li>
              <Link
                href="/reports"
                onClick={() => setOpen(false)}
                className="flex h-12 items-center rounded-lg px-2 text-base font-medium hover:bg-muted"
              >
                Open app
              </Link>
            </li>
          </ul>
          <ButtonLink
            href="/audits/new"

            size="lg"
            onClick={() => setOpen(false)}
            className="mt-3 mb-2 w-full"
          >
            Run an audit
          </ButtonLink>
        </nav>
      </div>
    </header>
  );
}
