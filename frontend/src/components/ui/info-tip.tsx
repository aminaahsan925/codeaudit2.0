"use client";

import { Popover } from "@base-ui/react/popover";
import { Info } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * A small "i" button that explains a term in plain English. A popover, not a
 * hover tooltip, so it works with touch and keyboard. The trigger has an
 * accessible name naming the term.
 */
export function InfoTip({
  term,
  children,
  className,
}: {
  term: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Popover.Root>
      <Popover.Trigger
        aria-label={`What is ${term}?`}
        className={cn(
          "inline-flex size-5 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
          className,
        )}
      >
        <Info aria-hidden="true" className="size-3.5" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner sideOffset={6} className="z-40">
          <Popover.Popup className="max-w-72 origin-(--transform-origin) rounded-xl border bg-popover p-3.5 text-sm text-popover-foreground shadow-float transition-[transform,opacity] duration-150 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0">
            <Popover.Title className="font-semibold">{term}</Popover.Title>
            <Popover.Description className="mt-1 text-muted-foreground">{children}</Popover.Description>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
