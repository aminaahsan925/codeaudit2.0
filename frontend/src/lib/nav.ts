export interface NavItem {
  href: "/audits/new" | "/reports";
  label: string;
}

export const MAIN_NAV: readonly NavItem[] = [
  { href: "/audits/new", label: "Run audit" },
  { href: "/reports", label: "Reports" },
];

export function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
