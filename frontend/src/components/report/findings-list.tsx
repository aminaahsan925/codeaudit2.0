"use client";

import * as m from "motion/react-m";

import { FindingCard } from "@/components/finding-card";
import { rowIn, stagger } from "@/components/ui/motion";
import type { Finding } from "@/lib/api";

/** Rows after this one appear without the entry animation. */
const STAGGER_CAP = 8;

/** The fix-first list. The first rows enter one after another. */
export function FindingsList({ findings, runId }: { findings: Finding[]; runId: string }) {
  return (
    <m.ol
      initial="hidden"
      animate="show"
      variants={stagger(0.06, 0.25)}
      className="flex flex-col gap-3"
    >
      {findings.map((finding, index) => (
        <FindingCard
          key={finding.id}
          finding={finding}
          index={index + 1}
          runId={runId}
          variants={index < STAGGER_CAP ? rowIn : undefined}
        />
      ))}
    </m.ol>
  );
}
