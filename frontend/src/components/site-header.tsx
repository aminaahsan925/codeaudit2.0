import { HealthBadge } from "@/components/health-badge";
import { MainNav } from "@/components/main-nav";
import { MobileNav } from "@/components/mobile-nav";
import { ThemeToggle } from "@/components/theme-toggle";
import { Wordmark } from "@/components/wordmark";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background">
      <div className="container-page flex h-16 items-center gap-3 md:gap-8">
        <Wordmark />
        <MainNav className="hidden md:block" />
        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <HealthBadge />
          <ThemeToggle />
          <MobileNav className="md:hidden" />
        </div>
      </div>
    </header>
  );
}
