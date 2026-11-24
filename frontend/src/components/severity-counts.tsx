import { SeverityBar } from "@/components/graphics/severity-bar";
import { SeverityMark } from "@/components/severity-badge";
import { SEVERITIES, SEVERITY_LABEL, type Severity } from "@/lib/report";
import { cn } from "@/lib/utils";

/**
 * The four severity counts as a ruled strip: number in mono, severity word
 * and shape beside it. Zero counts stay visible so the strip always reads
 * as a complete tally. The stacked bar underneath shows the same split as
 * a picture.
 */
export function SeverityCounts({
  counts,
  className,
}: {
  counts: Partial<Record<Severity, number>>;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-2.5", className)}>
      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-4">
        {SEVERITIES.map((severity) => (
          <div key={severity} className="flex flex-col gap-1 bg-card px-4 py-3">
            <dt className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <SeverityMark severity={severity} />
              {SEVERITY_LABEL[severity]}
            </dt>
            <dd className="font-mono text-2xl leading-none font-semibold tabular-nums">
              {counts[severity] ?? 0}
            </dd>
          </div>
        ))}
      </dl>
      <SeverityBar counts={counts} />
    </div>
  );
}
