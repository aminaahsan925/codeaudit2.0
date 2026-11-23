import Link from "next/link";

import { LogoMark } from "@/components/wordmark";
import { MAIN_NAV } from "@/lib/nav";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t">
      <div className="container-page flex flex-col gap-6 py-8 text-sm text-muted-foreground md:flex-row md:items-start md:justify-between">
        <div className="flex max-w-prose gap-3">
          <LogoMark className="mt-0.5 size-5" />
          <p>
            LaunchAudit checks AI-built web apps before launch. A report shows
            the evidence it found; it is not a guarantee that an app is secure.
          </p>
        </div>
        <nav aria-label="Footer">
          <ul className="flex gap-5">
            {MAIN_NAV.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="rounded-sm underline-offset-4 hover:text-foreground hover:underline"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
