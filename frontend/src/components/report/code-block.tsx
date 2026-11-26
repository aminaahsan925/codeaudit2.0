import { FileCode2 } from "lucide-react";

import type { Severity } from "@/lib/report";
import { cn } from "@/lib/utils";

const FLAGGED_LINE: Record<Severity, string> = {
  critical: "bg-sev-critical-tint shadow-[inset_3px_0_0_var(--sev-critical)]",
  high: "bg-sev-high-tint shadow-[inset_3px_0_0_var(--sev-high)]",
  medium: "bg-sev-medium-tint shadow-[inset_3px_0_0_var(--sev-medium)]",
  low: "bg-sev-low-tint shadow-[inset_3px_0_0_var(--sev-low)]",
};

/**
 * A code excerpt with line numbers. Lines inside the flagged range get the
 * severity tint, a bar on the left edge and a screen-reader note, so the
 * flag never depends on colour alone. Long lines scroll inside the block.
 */
export function CodeBlock({
  code,
  startLine,
  endLine,
  severity,
  caption,
  className,
}: {
  code: string;
  /** Line number of the first line of `code`; null hides the gutter. */
  startLine: number | null;
  endLine?: number | null;
  /** Severity of the flagged lines; omit for unflagged code. */
  severity?: Severity;
  caption?: string | null;
  className?: string;
}) {
  const lines = code.replace(/\n+$/, "").split("\n");
  const last = endLine ?? startLine;

  return (
    <figure
      className={cn("min-w-0 overflow-hidden rounded-xl border bg-sunken", className)}
    >
      {caption ? (
        <figcaption className="flex min-w-0 items-center gap-2 border-b px-3 py-2 font-mono text-xs text-muted-foreground">
          <FileCode2 aria-hidden="true" className="size-3.5 shrink-0" />
          <span className="truncate">{caption}</span>
        </figcaption>
      ) : null}
      <pre className="overflow-x-auto py-2 font-mono text-[0.8125rem] leading-6">
        <code className="grid min-w-max">
          {lines.map((line, i) => {
            const number = startLine !== null ? startLine + i : null;
            const flagged =
              severity !== undefined &&
              number !== null &&
              last !== null &&
              number >= (startLine ?? 0) &&
              number <= last;
            return (
              <span
                key={i}
                data-flagged={flagged || undefined}
                className={cn(
                  "grid pr-4",
                  number !== null ? "grid-cols-[3.25rem_1fr]" : "grid-cols-[0.75rem_1fr]",
                  flagged && severity ? FLAGGED_LINE[severity] : null,
                )}
              >
                <span
                  aria-hidden="true"
                  className="pr-3 text-right text-muted-foreground tabular-nums select-none"
                >
                  {number ?? ""}
                </span>
                <span className="whitespace-pre text-foreground">
                  {line === "" ? " " : line}
                  {flagged ? <span className="sr-only"> (flagged line)</span> : null}
                </span>
              </span>
            );
          })}
        </code>
      </pre>
    </figure>
  );
}
