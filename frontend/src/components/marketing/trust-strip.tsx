import { Database, Globe, KeyRound, Package, ShieldCheck, TextCursorInput, UsersRound } from "lucide-react";

const CHECKED = [
  { label: "Leaked keys", icon: KeyRound },
  { label: "Database rules", icon: Database },
  { label: "Who can see what", icon: UsersRound },
  { label: "Injection", icon: TextCursorInput },
  { label: "Outdated packages", icon: Package },
  { label: "Security headers", icon: Globe },
] as const;

/** Sits on the seam between the hero and the checks band. */
export function TrustStrip() {
  return (
    <section aria-label="What LaunchAudit checks" className="relative z-10 container-page -mb-16">
      <div className="grid grid-cols-1 gap-6 rounded-2xl border bg-card p-5 shadow-card sm:p-6 lg:grid-cols-12 lg:items-center lg:gap-8">
        <div className="flex items-start gap-3 lg:col-span-4">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-verdict-launch-tint text-verdict-launch-fg">
            <ShieldCheck aria-hidden="true" className="size-5" />
          </span>
          <div>
            <p className="font-display text-lg leading-6 font-semibold tracking-[-0.02em]">
              Your code is read, never run.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              We never install your packages or start your app.
            </p>
          </div>
        </div>
        <div className="lg:col-span-8 lg:border-l lg:pl-8">
          <p className="text-sm text-muted-foreground">Every audit checks for</p>
          <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
            {CHECKED.map(({ label, icon: Icon }) => (
              <li key={label} className="flex items-center gap-2 text-sm font-medium">
                <Icon aria-hidden="true" className="size-4 shrink-0 text-brand-fg" />
                {label}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
