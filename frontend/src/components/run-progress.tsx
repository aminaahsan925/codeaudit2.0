import { cn } from "@/lib/utils";

const TICKS = Array.from({ length: 11 }, (_, i) => i);

/**
 * The run instrument: the percentage the API reports over a ticked scale.
 * The bar is decorative; the number is the content. The number comes from
 * the run as is; nothing here estimates or interpolates it.
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
    <div className={cn("flex flex-col gap-2.5", className)}>
      <p className="flex items-baseline gap-2">
        <span className="font-heading text-[2.5rem] leading-none font-semibold tracking-[-0.025em] tabular-nums">
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
        <div className="relative h-2 overflow-hidden rounded-full bg-sunken ring-1 ring-border ring-inset">
          <div
            className="absolute inset-0 origin-left bg-foreground transition-transform duration-400 ease-out motion-reduce:transition-none"
            style={{ transform: `scaleX(${clamped / 100})` }}
          />
        </div>
        <div aria-hidden="true" className="mt-1.5 flex justify-between px-px">
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
