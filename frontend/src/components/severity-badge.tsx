import { cn } from "@/lib/utils";
import { SEVERITY_LABEL, type Severity } from "@/lib/report";

const tone: Record<Severity, string> = {
  critical:
    "bg-sev-critical-tint text-sev-critical-fg border-sev-critical/40 [--mark:var(--sev-critical)]",
  high: "bg-sev-high-tint text-sev-high-fg border-sev-high/40 [--mark:var(--sev-high)]",
  medium:
    "bg-sev-medium-tint text-sev-medium-fg border-sev-medium/40 [--mark:var(--sev-medium)]",
  low: "bg-sev-low-tint text-sev-low-fg border-sev-low/40 [--mark:var(--sev-low)]",
};

/**
 * One distinct shape per level so severity reads without colour:
 * octagon with a bar (stop), triangle (warning), diamond (caution), ring (note).
 */
export function SeverityMark({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  const shape = {
    critical: (
      <path
        fillRule="evenodd"
        d="M4.7 1h6.6L15 4.7v6.6L11.3 15H4.7L1 11.3V4.7zM7 4h2v5H7zm0 6h2v2H7z"
      />
    ),
    high: <polygon points="8,1.5 15,14.5 1,14.5" />,
    medium: <polygon points="8,1 15,8 8,15 1,8" />,
    low: (
      <circle cx="8" cy="8" r="5" fill="none" stroke="var(--mark)" strokeWidth="2.5" />
    ),
  }[severity];

  return (
    <svg
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
      className={cn("size-3.5 shrink-0 fill-(--mark)", className)}
    >
      {shape}
    </svg>
  );
}

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  return (
    <span
      data-severity={severity}
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded-sm border px-2 text-xs font-semibold whitespace-nowrap",
        tone[severity],
        className,
      )}
    >
      <SeverityMark severity={severity} />
      {SEVERITY_LABEL[severity]}
    </span>
  );
}
