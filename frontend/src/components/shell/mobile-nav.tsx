"use client";

import { Menu } from "lucide-react";
import { Suspense } from "react";

import { HealthBadge } from "@/components/health-badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Wordmark } from "@/components/wordmark";
import { cn } from "@/lib/utils";

import { NavList, NavListWithPathname } from "./nav-list";
import { useShell } from "./shell-context";
import { SafetyNote } from "./sidebar";

/** Below 1024px the sidebar opens as a drawer from the top bar menu button. */
export function MobileNav({ className }: { className?: string }) {
  const { drawerOpen, setDrawerOpen } = useShell();
  const close = () => setDrawerOpen(false);
  const navProps = { collapsed: false, animateLabels: false, onNavigate: close };

  return (
    <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
      <SheetTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            aria-label="Open menu"
            className={cn(
              "size-9 rounded-[10px] text-muted-foreground hover:bg-sunken hover:text-foreground",
              className,
            )}
          />
        }
      >
        <Menu aria-hidden="true" className="size-5" />
      </SheetTrigger>
      <SheetContent
        side="left"
        className="w-72 max-w-[85vw] gap-0 rounded-r-[20px] border-border bg-background shadow-float"
      >
        <div className="flex h-14 shrink-0 items-center px-6">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <SheetDescription className="sr-only">Main navigation</SheetDescription>
          <Wordmark className="font-heading text-[1.0625rem] font-semibold" />
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pt-3 pb-3">
          <Suspense fallback={<NavList pathname={null} {...navProps} />}>
            <NavListWithPathname {...navProps} />
          </Suspense>
        </div>
        <div className="flex shrink-0 flex-col gap-3 border-t border-border px-4 py-4">
          <SafetyNote className="px-[11px]" />
          <HealthBadge className="self-start" side="top" />
        </div>
      </SheetContent>
    </Sheet>
  );
}
