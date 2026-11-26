"use client";

import { Popover } from "@base-ui/react/popover";
import { Download, Share2 } from "lucide-react";

import { ButtonLink } from "@/components/button-link";
import { RerunButton } from "@/components/rerun-button";
import { ShareLink } from "@/components/share-link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function SharePopover({ path }: { path: string }) {
  return (
    <Popover.Root>
      <Popover.Trigger className={cn(buttonVariants({ variant: "outline" }))}>
        <Share2 aria-hidden="true" />
        <span className="max-sm:sr-only">Share</span>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner side="bottom" align="end" sideOffset={8} collisionPadding={16} className="z-40">
          <Popover.Popup className="w-[min(24rem,calc(100vw-2rem))] origin-(--transform-origin) rounded-2xl border bg-popover p-4 text-popover-foreground shadow-float transition-[transform,opacity] duration-150 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0">
            <Popover.Title className="font-heading text-base font-[550] tracking-[-0.02em]">
              Share this report
            </Popover.Title>
            <ShareLink path={path} className="mt-3" />
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}

/**
 * Rerun, PDF and Share. Fixed to the bottom of the screen on mobile; sticky
 * at the top of the findings column on desktop. The shared (read-only)
 * report swaps Rerun for "Run your own audit".
 */
export function ReportActions({
  runId,
  hasJourney,
  pdfUrl,
  sharePath,
  readOnly,
}: {
  runId: string;
  hasJourney: boolean;
  pdfUrl: string | null;
  sharePath: string | null;
  readOnly: boolean;
}) {
  const pdf = pdfUrl ? (
    <a
      href={pdfUrl}
      target="_blank"
      rel="noreferrer"
      className={cn(buttonVariants({ variant: "outline" }))}
    >
      <Download aria-hidden="true" />
      <span className="max-sm:sr-only">Download PDF</span>
    </a>
  ) : null;
  const share = sharePath ? <SharePopover path={sharePath} /> : null;

  return (
    <section
      aria-label="Report actions"
      className="glass fixed inset-x-0 bottom-0 z-30 border-t px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] lg:sticky lg:top-(--report-sticky-top) lg:bottom-auto lg:rounded-2xl lg:border lg:p-2.5 lg:shadow-card"
    >
      {readOnly ? (
        <div className="flex items-center gap-2">
          <ButtonLink href="/audits/new">Run your own audit</ButtonLink>
          <div className="ml-auto flex items-center gap-2">
            {pdf}
            {share}
          </div>
        </div>
      ) : (
        <RerunButton runId={runId} hasJourney={hasJourney}>
          {pdf}
          {share}
        </RerunButton>
      )}
    </section>
  );
}
