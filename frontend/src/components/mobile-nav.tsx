"use client";

import { Menu } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { MAIN_NAV, isActivePath } from "@/lib/nav";
import { cn } from "@/lib/utils";

export function MobileNav({ className }: { className?: string }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            aria-label="Open menu"
            className={cn("size-9", className)}
          />
        }
      >
        <Menu aria-hidden="true" className="size-5" />
      </SheetTrigger>
      <SheetContent side="right" className="w-72 max-w-[85vw]">
        <SheetHeader>
          <SheetTitle>Menu</SheetTitle>
          <SheetDescription className="sr-only">
            Main navigation
          </SheetDescription>
        </SheetHeader>
        <nav aria-label="Main" className="px-4">
          <ul className="flex flex-col gap-1">
            {MAIN_NAV.map((item) => {
              const active = isActivePath(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex h-11 items-center rounded-md border-l-2 px-3 text-base font-medium",
                      active
                        ? "border-primary bg-muted text-foreground"
                        : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </SheetContent>
    </Sheet>
  );
}
