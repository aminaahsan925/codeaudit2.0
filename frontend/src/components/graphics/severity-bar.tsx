import { SEVERITIES, type Severity } from "@/lib/report";
import { cn } from "@/lib/utils";

const SEGMENT_BG: Record<Severity, string> = {
  critical: "bg-sev-critical",
  high: "bg-sev-high",
  medium: "bg-sev-medium",
  low: "bg-sev-low",
};

/**
 * Stacked severity bar: each segment's width is its share of all findings,
 * coloured with the severity token. Decorative; the counts strip beside it
 * carries the numbers.
 */
export function SeverityBar({
  counts,
  className,
}: {
  counts: Partial<Record<Severity, number>>;
  className?: string;
}) {
  const total = SEVERITIES.reduce((sum, severity) => sum + (counts[severity] ?? 0), 0);

  return (
    <div
      data-testid="severity-bar"
      aria-hidden="true"
      className={cn(
        "flex h-2.5 w-full overflow-hidden rounded-full bg-muted",
        className,
      )}
    >
      {total > 0
        ? SEVERITIES.map((severity) => {
            const count = counts[severity] ?? 0;
            if (count === 0) return null;
            return (
              <div
                key={severity}
                data-severity={severity}
                className={SEGMENT_BG[severity]}
                style={{ width: `${(count / total) * 100}%` }}
              />
            );
          })
        : null}
    </div>
  );
}
