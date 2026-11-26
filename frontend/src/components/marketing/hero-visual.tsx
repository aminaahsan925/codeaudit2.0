import { Lock } from "lucide-react";

import { SampleReport, SampleVerdictCard } from "@/components/sample-report";
import { SAMPLE_PROJECT } from "@/lib/sample-data";
import { cn } from "@/lib/utils";

import { Replay } from "./replay";

/**
 * The hero's live product card: the example audit inside a browser frame,
 * tilted in 3D on large screens (transform only), with the verdict card
 * floating over its lower edge.
 */
export function HeroVisual({ className }: { className?: string }) {
  return (
    <figure className={cn("relative", className)} aria-labelledby="hero-visual-caption">
      <div className="animate-in fade-in slide-in-from-bottom-6 duration-700 fill-mode-both ease-out lg:[perspective:2400px]">
        <div className="relative transform-gpu lg:[transform:rotateY(-10deg)_rotateX(5deg)] lg:[transform-style:preserve-3d]">
          <Replay
            label="Replay"
            accessibleLabel="Replay the example audit"
            buttonClassName="absolute top-1.5 right-2 z-10 sm:right-3"
          >
            <div className="overflow-hidden rounded-2xl border bg-card shadow-float">
              <div className="flex h-10 items-center gap-3 border-b bg-sunken px-4">
                <span aria-hidden="true" className="flex gap-1.5">
                  <span className="size-2.5 rounded-full bg-border" />
                  <span className="size-2.5 rounded-full bg-border" />
                  <span className="size-2.5 rounded-full bg-border" />
                </span>
                <p className="mr-16 flex h-6 min-w-0 flex-1 items-center justify-center gap-1.5 rounded-md bg-card px-3 text-xs text-muted-foreground shadow-xs sm:mx-auto sm:max-w-72">
                  <Lock aria-hidden="true" className="size-3 shrink-0" />
                  <span className="truncate">Launch Report for {SAMPLE_PROJECT.name}</span>
                </p>
              </div>
              <SampleReport className="lg:pb-[4.5rem]" />
            </div>
            <SampleVerdictCard className="relative z-10 mx-4 -mt-6 sm:mr-6 sm:ml-auto sm:w-[23rem] lg:absolute lg:-bottom-10 lg:-left-12 lg:m-0 lg:[transform:translateZ(48px)]" />
          </Replay>
        </div>
      </div>
      <figcaption
        id="hero-visual-caption"
        className="mt-5 text-center text-sm text-muted-foreground lg:mt-16 lg:pr-4 lg:text-right"
      >
        An example audit of {SAMPLE_PROJECT.name}, a fictional app.
      </figcaption>
    </figure>
  );
}
