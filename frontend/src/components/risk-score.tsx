import { formatRiskScore } from "@/lib/report";
import { cn } from "@/lib/utils";

const TICKS = Array.from({ length: 11 }, (_, i) => i);

/**
 * 0-10 risk score: the number is the content, the instrument-style scale
 * underneath is decorative (hidden from assistive tech).
 */
export function RiskScore({
  score,
  className,
}: {
  score: number;
  className?: string;
}) {
  const value = formatRiskScore(score);
  const fraction = Number(value) / 10;

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <p className="flex items-baseline gap-1.5">
        <span className="font-mono text-4xl leading-none font-semibold tracking-tight tabular-nums">
          {value}
        </span>
        <span className="text-sm text-muted-foreground">
          <span aria-hidden="true">/ 10</span>
          <span className="sr-only">out of 10</span>
        </span>
      </p>
      <div aria-hidden="true" className="w-full">
        <div className="relative h-2 overflow-hidden rounded-[2px] bg-muted">
          <div
            className="absolute inset-y-0 left-0 origin-left animate-gauge bg-foreground"
            style={{ width: `${fraction * 100}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between">
          {TICKS.map((tick) => (
            <span
              key={tick}
              className={cn(
                "w-px bg-input",
                tick % 5 === 0 ? "h-2" : "h-1",
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
