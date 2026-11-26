import Link from "next/link";

import { Wordmark } from "@/components/wordmark";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "/audits/new", label: "Run an audit" },
      { href: "/reports", label: "Your reports" },
      { href: "/#example", label: "Example report" },
    ],
  },
  {
    title: "Learn",
    links: [
      { href: "/#how-it-works", label: "How it works" },
      { href: "/#checks", label: "What we check" },
      { href: "/#faq", label: "Questions" },
    ],
  },
] as const;

const TRUST = [
  "Your code is read, never run.",
  "Live checks only on sites you verify.",
  "Keys are masked in every report.",
] as const;

export function MarketingFooter() {
  return (
    <footer className="border-t bg-sunken">
      <div className="container-page grid grid-cols-1 gap-10 py-14 sm:grid-cols-2 lg:grid-cols-12 lg:gap-8">
        <div className="flex flex-col items-start gap-3 sm:col-span-2 lg:col-span-4">
          <Wordmark />
          <p className="max-w-xs text-sm text-muted-foreground">
            Launch checks for apps built with AI tools, explained in plain words.
          </p>
        </div>
        {COLUMNS.map((column) => (
          <nav key={column.title} aria-labelledby={`footer-${column.title}`} className="lg:col-span-2">
            <h2 id={`footer-${column.title}`} className="font-sans text-sm font-semibold tracking-normal">
              {column.title}
            </h2>
            <ul className="mt-4 flex flex-col gap-3 text-sm">
              {column.links.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="rounded-sm text-muted-foreground hover:text-foreground">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
        <div className="sm:col-span-2 lg:col-span-4">
          <h2 className="font-sans text-sm font-semibold tracking-normal">Trust</h2>
          <ul className="mt-4 flex flex-col gap-3 text-sm text-muted-foreground">
            {TRUST.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      </div>
      <div className="border-t">
        <p className="container-page py-6 text-sm text-muted-foreground">
          LaunchAudit finds common security problems. It is not a guarantee that your app is secure.
        </p>
      </div>
    </footer>
  );
}
