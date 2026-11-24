import { RiskGauge } from "@/components/graphics/risk-gauge";
import { formatRiskScore } from "@/lib/report";
import { cn } from "@/lib/utils";

/**
 * 0-10 risk score: the number is the content, the gauge dial underneath
 * is decorative (hidden from assistive tech).
 */
export function RiskScore({
  score,
  className,
}: {
  score: number;
  className?: string;
}) {
  const value = formatRiskScore(score);

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
      <RiskGauge score={score} className="w-40" />
    </div>
  );
}
