import { CircleCheck, OctagonX, TriangleAlert, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { VERDICT_LABEL, type Verdict } from "@/lib/report";

const config: Record<Verdict, { icon: LucideIcon; tone: string; iconTone: string }> = {
  launch: {
    icon: CircleCheck,
    tone: "bg-verdict-launch-tint text-verdict-launch-fg border-verdict-launch/45",
    iconTone: "text-verdict-launch",
  },
  fix_first: {
    icon: TriangleAlert,
    tone: "bg-verdict-fix-tint text-verdict-fix-fg border-verdict-fix/45",
    iconTone: "text-verdict-fix",
  },
  do_not_launch: {
    icon: OctagonX,
    tone: "bg-verdict-block-tint text-verdict-block-fg border-verdict-block/45",
    iconTone: "text-verdict-block",
  },
};

const sizes = {
  sm: "h-6 gap-1.5 px-2 text-xs [&_svg]:size-3.5",
  md: "h-8 gap-2 px-2.5 text-sm [&_svg]:size-4",
  lg: "h-11 gap-2.5 px-3.5 text-lg [&_svg]:size-5",
} as const;

export function VerdictBadge({
  verdict,
  size = "md",
  className,
}: {
  verdict: Verdict;
  size?: keyof typeof sizes;
  className?: string;
}) {
  const { icon: Icon, tone, iconTone } = config[verdict];
  return (
    <span
      data-verdict={verdict}
      className={cn(
        "inline-flex items-center rounded-md border font-semibold whitespace-nowrap",
        sizes[size],
        tone,
        className,
      )}
    >
      <Icon aria-hidden="true" strokeWidth={2.25} className={cn("shrink-0", iconTone)} />
      {VERDICT_LABEL[verdict]}
    </span>
  );
}
