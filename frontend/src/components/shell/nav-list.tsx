"use client";

import { CircleHelp, FilePlus2, ListChecks, type LucideIcon } from "lucide-react";
import * as m from "motion/react-m";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactElement } from "react";

import { EASE_OUT } from "@/components/ui/motion";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  HELP_NAV,
  PRIMARY_NAV,
  isActivePath,
  type NavId,
  type NavLinkItem,
} from "@/lib/nav";
import { cn } from "@/lib/utils";

const ICONS: Record<NavId, LucideIcon> = {
  "new-audit": FilePlus2,
  reports: ListChecks,
  help: CircleHelp,
};

/*
  Icons sit at the same x in the rail and the full sidebar (11px inset in a
  40px item), so collapsing never moves them; only the labels change.
*/
const itemBase =
  "relative flex h-9 w-full items-center gap-3 rounded-[10px] px-[11px] text-sm font-medium outline-none transition-colors focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-solid focus-visible:outline-ring";

interface ListProps {
  /** Null while the pathname is not known yet (the Suspense fallback). */
  pathname: string | null;
  collapsed: boolean;
  /** Animate labels in: true right after the user expands the sidebar. */
  animateLabels: boolean;
  onNavigate?: () => void;
}

function Label({
  children,
  collapsed,
  animate,
}: {
  children: string;
  collapsed: boolean;
  animate: boolean;
}) {
  if (collapsed) return <span className="sr-only">{children}</span>;
  return (
    <m.span
      className="truncate"
      initial={animate ? { opacity: 0, x: -6 } : false}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, ease: EASE_OUT }}
    >
      {children}
    </m.span>
  );
}

function RailTooltip({
  collapsed,
  label,
  trigger,
}: {
  collapsed: boolean;
  label: string;
  trigger: ReactElement;
}) {
  if (!collapsed) return trigger;
  return (
    <Tooltip>
      <TooltipTrigger render={trigger} />
      <TooltipContent side="right" sideOffset={10}>
        {label}
      </TooltipContent>
    </Tooltip>
  );
}

function LinkRow({
  item,
  pathname,
  collapsed,
  animateLabels,
  onNavigate,
}: { item: NavLinkItem } & ListProps) {
  const Icon = ICONS[item.id];
  const active = item.trackActive && pathname !== null && isActivePath(pathname, item.href);

  return (
    <li>
      <RailTooltip
        collapsed={collapsed}
        label={item.label}
        trigger={
          <Link
            href={item.href}
            aria-current={active ? "page" : undefined}
            onClick={onNavigate}
            className={cn(
              itemBase,
              active
                ? "bg-brand-soft font-semibold text-brand-fg before:absolute before:inset-y-2 before:left-0 before:w-[3px] before:rounded-full before:bg-brand"
                : "text-muted-foreground hover:bg-sunken hover:text-foreground",
            )}
          >
            <Icon aria-hidden="true" className="size-[18px] shrink-0" strokeWidth={active ? 2.2 : 1.9} />
            <Label collapsed={collapsed} animate={animateLabels}>
              {item.label}
            </Label>
          </Link>
        }
      />
    </li>
  );
}

export function NavList(props: ListProps) {
  return (
    <nav aria-label="Main" className="flex flex-1 flex-col">
      <ul className="flex flex-col gap-0.5">
        {PRIMARY_NAV.map((item) => (
          <LinkRow key={item.id} item={item} {...props} />
        ))}
      </ul>
      <ul className="mt-auto flex flex-col gap-0.5 pt-3">
        <LinkRow item={HELP_NAV} {...props} />
      </ul>
    </nav>
  );
}

/** The nav with the current page marked. Render inside <Suspense>. */
export function NavListWithPathname(props: Omit<ListProps, "pathname">) {
  const pathname = usePathname();
  return <NavList pathname={pathname} {...props} />;
}
