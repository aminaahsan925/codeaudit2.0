"use client";

import { PanelLeftClose, PanelLeftOpen, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { HealthBadge } from "@/components/health-badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { LogoMark, Wordmark } from "@/components/wordmark";
import { cn } from "@/lib/utils";

import { NavList, NavListWithPathname } from "./nav-list";
import { useShell } from "./shell-context";

export const SIDEBAR_ID = "app-sidebar";

/** The read-only promise, shown under the nav. */
export function SafetyNote({ className }: { className?: string }) {
  return (
    <p className={cn("flex items-start gap-2 text-xs text-muted-foreground", className)}>
      <ShieldCheck aria-hidden="true" className="mt-px size-4 shrink-0 text-brand" />
      <span>Your code is read, never run.</span>
    </p>
  );
}

function CollapseButton() {
  const { collapsed, toggleCollapsed } = useShell();
  const label = collapsed ? "Expand sidebar" : "Collapse sidebar";
  const Icon = collapsed ? PanelLeftOpen : PanelLeftClose;
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label={label}
            aria-expanded={!collapsed}
            aria-controls={SIDEBAR_ID}
            className="inline-flex size-8 shrink-0 items-center justify-center rounded-[8px] text-muted-foreground transition-colors hover:bg-sunken hover:text-foreground"
          />
        }
      >
        <Icon aria-hidden="true" className="size-[18px]" strokeWidth={1.9} />
      </TooltipTrigger>
      <TooltipContent side="right" sideOffset={8}>
        {label}
      </TooltipContent>
    </Tooltip>
  );
}

/**
 * Desktop sidebar (1024px and up). Collapsing swaps the width in one step and
 * fades the labels back in on expand; no width animation.
 */
export function Sidebar() {
  const { collapsed, collapseChanged } = useShell();
  const navProps = { collapsed, animateLabels: collapseChanged };

  return (
    <aside
      id={SIDEBAR_ID}
      aria-label="Sidebar"
      data-collapsed={collapsed ? "" : undefined}
      className={cn(
        "sticky top-0 z-30 hidden h-dvh shrink-0 flex-col border-r border-border bg-background lg:flex",
        collapsed ? "w-[4.5rem]" : "w-60",
      )}
    >
      <div className={cn("flex h-14 shrink-0 items-center", collapsed ? "justify-center" : "px-6")}>
        {collapsed ? (
          <Link
            href="/"
            aria-label="LaunchAudit home"
            className="inline-flex size-10 items-center justify-center rounded-[10px]"
          >
            <LogoMark />
          </Link>
        ) : (
          <Wordmark className="font-heading text-[1.0625rem] font-semibold" />
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pt-3 pb-3">
        {/*
          The nav reads the pathname to mark the current page. With
          cacheComponents that is request data on dynamic routes, so it streams
          in behind Suspense; the fallback is the same list with nothing marked.
        */}
        <Suspense fallback={<NavList pathname={null} {...navProps} />}>
          <NavListWithPathname {...navProps} />
        </Suspense>
      </div>

      <div
        className={cn(
          "flex shrink-0 flex-col gap-3 border-t border-border py-4",
          collapsed ? "items-center px-2" : "px-4",
        )}
      >
        {collapsed ? null : <SafetyNote className="px-[11px]" />}
        <div className={cn("flex items-center gap-2", collapsed ? "flex-col" : "justify-between")}>
          <HealthBadge compact={collapsed} side={collapsed ? "right" : "top"} />
          <CollapseButton />
        </div>
      </div>
    </aside>
  );
}
