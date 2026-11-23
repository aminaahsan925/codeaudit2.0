import { cn } from "@/lib/utils";

const TICKS = Array.from({ length: 11 }, (_, i) => i);

/**
 * The run instrument: a large mono percentage over a ticked scale, echoing
 * the risk score gauge. The bar is decorative; the number is the content.
 */
export function RunProgress({
  progress,
  className,
}: {
  progress: number;
  className?: string;
}) {
  const clamped = Math.min(100, Math.max(0, Math.round(progress)));
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <p className="flex items-baseline gap-1.5">
        <span className="font-mono text-4xl leading-none font-semibold tracking-tight tabular-nums">
          {clamped}
        </span>
        <span className="text-sm text-muted-foreground">percent complete</span>
      </p>
      <div
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Audit progress"
        className="w-full"
      >
        <div className="relative h-2 overflow-hidden rounded-[2px] bg-muted">
          <div
            className="absolute inset-y-0 left-0 bg-foreground transition-[width] duration-500"
            style={{ width: `${clamped}%` }}
          />
        </div>
        <div aria-hidden="true" className="mt-1 flex justify-between">
          {TICKS.map((tick) => (
            <span
              key={tick}
              className={cn("w-px bg-input", tick % 5 === 0 ? "h-2" : "h-1")}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
