import {
  CircleCheck,
  CircleMinus,
  Clock,
  LoaderCircle,
  OctagonX,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { RUN_STATUS_LABEL, type AuditRunStatus } from "@/lib/report";

const config: Record<
  AuditRunStatus,
  { icon: LucideIcon; tone: string; spin?: boolean }
> = {
  queued: {
    icon: Clock,
    tone: "bg-muted text-muted-foreground border-border",
  },
  running: {
    icon: LoaderCircle,
    tone: "bg-muted text-foreground border-border",
    spin: true,
  },
  succeeded: {
    icon: CircleCheck,
    tone: "bg-verdict-launch-tint text-verdict-launch-fg border-verdict-launch/45",
  },
  failed: {
    icon: OctagonX,
    tone: "bg-sev-critical-tint text-sev-critical-fg border-sev-critical/40",
  },
  cancelled: {
    icon: CircleMinus,
    tone: "bg-muted text-muted-foreground border-border",
  },
};

export function RunStatusBadge({
  status,
  className,
}: {
  status: AuditRunStatus;
  className?: string;
}) {
  const { icon: Icon, tone, spin } = config[status];
  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded-sm border px-2 text-xs font-semibold whitespace-nowrap",
        tone,
        className,
      )}
    >
      <Icon
        aria-hidden="true"
        className={cn("size-3.5 shrink-0", spin && "animate-spin")}
      />
      {RUN_STATUS_LABEL[status]}
    </span>
  );
}
