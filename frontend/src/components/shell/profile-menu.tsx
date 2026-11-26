"use client";

import { Menu } from "@base-ui/react/menu";
import { ChevronDown, CircleHelp, LogIn, UserRound } from "lucide-react";
import Link from "next/link";

const itemClass =
  "flex h-9 w-full items-center gap-2.5 rounded-[8px] px-2.5 text-sm outline-none select-none data-highlighted:bg-sunken data-disabled:cursor-default data-disabled:text-muted-foreground";

/** Account menu. Shows Guest until sign-in exists. */
export function ProfileMenu() {
  return (
    <Menu.Root>
      <Menu.Trigger
        aria-label="Guest account"
        className="inline-flex h-9 items-center gap-2 rounded-full p-1 text-sm font-medium text-foreground transition-colors hover:bg-sunken aria-expanded:bg-sunken sm:pr-2.5"
      >
        <span
          aria-hidden="true"
          className="inline-flex size-7 items-center justify-center rounded-full border border-border bg-card text-muted-foreground"
        >
          <UserRound className="size-4" strokeWidth={1.9} />
        </span>
        <span aria-hidden="true" className="hidden sm:inline">
          Guest
        </span>
        <ChevronDown aria-hidden="true" className="hidden size-3.5 text-muted-foreground sm:block" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner side="bottom" align="end" sideOffset={8} className="z-40 outline-none">
          <Menu.Popup className="w-72 origin-(--transform-origin) rounded-2xl border border-border bg-popover p-1.5 text-popover-foreground shadow-float outline-none transition-[opacity,transform] duration-150 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0">
            <div className="flex items-center gap-3 px-2.5 pt-2 pb-2.5">
              <span
                aria-hidden="true"
                className="inline-flex size-9 shrink-0 items-center justify-center rounded-full border border-border bg-sunken text-muted-foreground"
              >
                <UserRound className="size-[18px]" strokeWidth={1.9} />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold">Guest</p>
                <p className="text-xs text-muted-foreground">Reports stay in this browser.</p>
              </div>
            </div>
            <Menu.Separator className="mx-1 my-1 h-px bg-border" />
            <Menu.Item disabled className={itemClass}>
              <LogIn aria-hidden="true" className="size-4" />
              Sign in (coming soon)
            </Menu.Item>
            <Menu.LinkItem render={<Link href="/#faq" />} className={itemClass}>
              <CircleHelp aria-hidden="true" className="size-4 text-muted-foreground" />
              Help and FAQ
            </Menu.LinkItem>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}
