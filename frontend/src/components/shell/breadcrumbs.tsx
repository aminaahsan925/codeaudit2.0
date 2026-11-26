"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment } from "react";

import { getBreadcrumbs } from "@/lib/nav";
import { cn } from "@/lib/utils";

/** Breadcrumbs from the pathname. Render inside <Suspense> (reads request data). */
export function Breadcrumbs({ className }: { className?: string }) {
  const pathname = usePathname();
  const crumbs = getBreadcrumbs(pathname);
  if (crumbs.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className={cn("min-w-0", className)}>
      <ol className="flex min-w-0 items-center gap-1.5 text-sm">
        {crumbs.map((crumb, index) => {
          const last = index === crumbs.length - 1;
          return (
            <Fragment key={crumb.label}>
              <li className={cn("min-w-0", !last && "hidden shrink-0 sm:block")}>
                {crumb.href && !last ? (
                  <Link
                    href={crumb.href}
                    className="rounded-[6px] text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span aria-current="page" className="block truncate font-medium text-foreground">
                    {crumb.label}
                  </span>
                )}
              </li>
              {last ? null : (
                <li aria-hidden="true" className="hidden shrink-0 text-muted-foreground sm:block">
                  <ChevronRight className="size-3.5" />
                </li>
              )}
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
