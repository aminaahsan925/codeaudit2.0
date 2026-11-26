import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export const inputClasses =
  "h-10 w-full rounded-[10px] border border-input bg-card px-3 text-sm text-foreground outline-none transition-[border-color,box-shadow] placeholder:text-muted-foreground/80 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 aria-invalid:border-sev-critical disabled:opacity-60";

export const monoInputClasses = cn(inputClasses, "font-mono text-[0.8125rem]");

/** Joins the ids that describe a control, skipping the empty ones. */
export function describedBy(...ids: (string | false | null | undefined)[]): string | undefined {
  const list = ids.filter(Boolean);
  return list.length > 0 ? list.join(" ") : undefined;
}

export function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} role="alert" className="flex items-start gap-1.5 text-sm text-sev-critical-fg">
      <span
        aria-hidden="true"
        className="mt-[0.4rem] size-1.5 shrink-0 rotate-45 bg-sev-critical"
      />
      {message}
    </p>
  );
}

export function FieldHint({ id, children }: { id: string; children: ReactNode }) {
  return (
    <p id={id} className="text-[0.8125rem] leading-5 text-muted-foreground">
      {children}
    </p>
  );
}

/** Label row: the label text, plus an optional info tip beside it. */
export function FieldLabel({
  htmlFor,
  children,
  tip,
}: {
  htmlFor: string;
  children: ReactNode;
  tip?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-1">
      <label htmlFor={htmlFor} className="text-sm font-medium text-foreground">
        {children}
      </label>
      {tip}
    </div>
  );
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
