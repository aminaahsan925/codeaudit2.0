"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { MAIN_NAV, isActivePath } from "@/lib/nav";
import { cn } from "@/lib/utils";

export function MainNav({ className }: { className?: string }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Main" className={className}>
      <ul className="flex items-center gap-1">
        {MAIN_NAV.map((item) => {
          const active = isActivePath(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative inline-flex h-9 items-center rounded-md px-3 text-sm font-medium transition-colors",
                  "after:absolute after:inset-x-3 after:-bottom-[13px] after:h-0.5 after:rounded-full",
                  active
                    ? "text-foreground after:bg-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
