import { cn } from "@/lib/utils";

export type RiskBand = "launch" | "fix" | "block";

/**
 * Verdict band for a 0-10 risk score, matching the backend thresholds
 * (launch at 2.0 and below, fix first up to 5.0, do not launch above).
 */
export function riskBand(score: number): RiskBand {
  if (score <= 2) return "launch";
  if (score <= 5) return "fix";
  return "block";
}

const BAND_STROKE: Record<RiskBand, string> = {
  launch: "stroke-verdict-launch",
  fix: "stroke-verdict-fix",
  block: "stroke-verdict-block",
};

/** Semicircle arc, centre (80, 84), radius 64. */
const ARC_PATH = "M 16 84 A 64 64 0 0 1 144 84";

/** Ticks at the scale ends and the two verdict boundaries. */
const TICKS = [0, 2, 5, 10];

function tickPoint(value: number, radius: number): [number, number] {
  const angle = Math.PI - (value / 10) * Math.PI;
  return [80 + radius * Math.cos(angle), 84 - radius * Math.sin(angle)];
}

/**
 * Semicircle risk gauge: the value arc fills in proportion to the 0-10
 * score and takes the colour of its verdict band. Decorative; the score
 * number beside it is the content.
 */
export function RiskGauge({
  score,
  className,
}: {
  score: number;
  className?: string;
}) {
  const clamped = Math.min(10, Math.max(0, score));
  const fraction = clamped / 10;

  return (
    <svg
      viewBox="0 0 160 96"
      data-testid="risk-gauge"
      aria-hidden="true"
      focusable="false"
      className={cn("h-auto w-full", className)}
    >
      <path
        d={ARC_PATH}
        fill="none"
        className="stroke-muted"
        strokeWidth="12"
        strokeLinecap="round"
      />
      <path
        d={ARC_PATH}
        data-testid="risk-gauge-arc"
        fill="none"
        className={BAND_STROKE[riskBand(clamped)]}
        strokeWidth="12"
        strokeLinecap="round"
        pathLength={100}
        strokeDasharray={`${fraction * 100} 100`}
      />
      {TICKS.map((tick) => {
        const [x1, y1] = tickPoint(tick, 74);
        const [x2, y2] = tickPoint(tick, 80);
        return (
          <line
            key={tick}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            className="stroke-input"
            strokeWidth="1.5"
          />
        );
      })}
      <text
        x="16"
        y="94"
        textAnchor="middle"
        fontSize="9"
        className="fill-muted-foreground font-mono"
      >
        0
      </text>
      <text
        x="144"
        y="94"
        textAnchor="middle"
        fontSize="9"
        className="fill-muted-foreground font-mono"
      >
        10
      </text>
    </svg>
  );
}
