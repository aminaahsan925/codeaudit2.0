import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/** Full-page state inside the shell: 404, route errors. */
export function StatusPage({
  icon: Icon,
  title,
  children,
  reference,
  actions,
}: {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
  /** Shown as "Reference" with a monospace id, for support. */
  reference?: string | null;
  actions: ReactNode;
}) {
  return (
    <div className="container-page flex flex-1 flex-col py-16 sm:py-24">
      <div className="flex max-w-[34rem] flex-col items-start">
        <span className="inline-flex size-12 items-center justify-center rounded-2xl border border-border bg-card text-muted-foreground shadow-card">
          <Icon aria-hidden="true" className="size-[22px]" strokeWidth={1.8} />
        </span>
        <h1 className="mt-6 font-display text-4xl text-foreground">{title}</h1>
        <div className="mt-3 text-lg text-muted-foreground">{children}</div>
        {reference ? (
          <p className="mt-5 inline-flex items-center gap-2 rounded-[8px] border border-border bg-sunken px-2.5 py-1 text-sm text-muted-foreground">
            Reference
            <code className="font-mono text-xs text-foreground">{reference}</code>
          </p>
        ) : null}
        <div className="mt-8 flex flex-wrap gap-3">{actions}</div>
      </div>
    </div>
  );
}
