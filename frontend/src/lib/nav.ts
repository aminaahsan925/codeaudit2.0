/*
  App shell navigation model: sidebar items and breadcrumb labels.
  Icons are attached in the shell components; this file stays plain data
  so it can be tested without rendering.
*/

export type NavId = "new-audit" | "reports" | "help";

export interface NavLinkItem {
  kind: "link";
  id: NavId;
  href: "/audits/new" | "/reports" | "/#faq";
  label: string;
  /** Whether the item can be the current page. Help leaves the app. */
  trackActive: boolean;
}

/*
  Projects and Settings are not in the nav until those features exist; an
  item that goes nowhere is noise in a short list.
*/
export const PRIMARY_NAV: readonly NavLinkItem[] = [
  { kind: "link", id: "new-audit", href: "/audits/new", label: "New audit", trackActive: true },
  { kind: "link", id: "reports", href: "/reports", label: "Reports", trackActive: true },
];

export const HELP_NAV: NavLinkItem = {
  kind: "link",
  id: "help",
  href: "/#faq",
  label: "Help",
  trackActive: false,
};

export function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export interface Crumb {
  label: string;
  /** Set for parent crumbs; the last crumb is the current page. */
  href?: "/reports";
}

/**
 * Breadcrumbs for an app pathname. Ids and tokens are never shown, only
 * labels. Returns an empty list for the home page.
 */
export function getBreadcrumbs(pathname: string): Crumb[] {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 0) return [];

  const [section, child, ...rest] = parts;

  if (section === "reports") {
    if (child === undefined) return [{ label: "Reports" }];
    if (rest.length === 0) return [{ label: "Reports", href: "/reports" }, { label: "Report" }];
  }
  if (section === "audits") {
    if (child === "new") return [{ label: "New audit" }];
    if (child !== undefined && rest.length === 0) return [{ label: "Audit run" }];
  }
  if (section === "sign-in" && child === undefined) return [{ label: "Sign in" }];
  if (section === "r" && child !== undefined && rest.length === 0) {
    return [{ label: "Shared report" }];
  }
  return [{ label: "Page not found" }];
}
