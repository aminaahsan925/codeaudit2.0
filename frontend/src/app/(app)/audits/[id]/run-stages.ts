import type { AuditRun } from "@/lib/api";

/*
  The run page pipeline, derived only from fields the run already returns.

  The API has no per-stage field, but the runner writes fixed progress
  values as it finishes each stage (backend/app/services/runs/runner.py):
  5 running, 15 code fetched, 40 code scan done, 60 live checks done,
  80 journey done, 85 dedupe done, 90 AI review done, 100 finished.
  On failure progress stays where it was, so it also names the stage that
  failed. Live checks and the journey need a live URL, so a run without one
  skips both.
*/

export type StageId = "fetch" | "scan" | "live" | "journey" | "review" | "report";

export type StageState = "pending" | "running" | "done" | "failed" | "skipped" | "not_run";

export interface StageDef {
  id: StageId;
  label: string;
  /** What the stage does, in plain words. */
  detail: string;
  /** What to do when this stage is the one that failed. */
  failureHint: string;
  /** Progress at which the stage starts and the value written when it ends. */
  start: number;
  end: number;
  needsLiveUrl?: boolean;
}

export const STAGES: readonly StageDef[] = [
  {
    id: "fetch",
    label: "Get the code",
    detail: "Clone the GitHub repo or unpack the zip.",
    failureHint:
      "Check that the GitHub repo is public and the URL is right, or upload the code as a zip.",
    start: 0,
    end: 15,
  },
  {
    id: "scan",
    label: "Scan the code",
    detail: "Look for leaked keys, injection, weak access rules and risky packages.",
    failureHint: "Try again. If it fails again, upload a smaller zip without build output.",
    start: 15,
    end: 40,
  },
  {
    id: "live",
    label: "Check the live site",
    detail: "Probe headers, cookies and exposed files on the live URL.",
    failureHint: "Check that the live site is up and reachable from the internet.",
    start: 40,
    end: 60,
    needsLiveUrl: true,
  },
  {
    id: "journey",
    label: "Walk the login journey",
    detail: "Sign up, log in and try the main flows with the test login.",
    failureHint: "Check that the test login works on the live site.",
    start: 60,
    end: 80,
    needsLiveUrl: true,
  },
  {
    id: "review",
    label: "Review the findings",
    detail: "Merge duplicates and double-check each finding.",
    failureHint: "Try again in a minute.",
    start: 80,
    end: 90,
  },
  {
    id: "report",
    label: "Write the report",
    detail: "Score the risk and pick the verdict.",
    failureHint: "Try again in a minute.",
    start: 90,
    end: 100,
  },
];

export const STAGE_STATE_LABEL: Record<StageState, string> = {
  pending: "Waiting",
  running: "Running",
  done: "Done",
  failed: "Failed",
  skipped: "Skipped",
  not_run: "Not run",
};

export interface StageView extends StageDef {
  state: StageState;
}

type RunFields = Pick<AuditRun, "status" | "progress" | "live_url">;

/**
 * The stage that holds a progress value: the last one whose start it has
 * reached. A skipped stage passes to the next one that runs (the last stage
 * never skips).
 */
function stageIndexAt(progress: number, skippable: (stage: StageDef) => boolean): number {
  let index = 0;
  STAGES.forEach((stage, i) => {
    if (progress >= stage.start) index = i;
  });
  while (index < STAGES.length - 1 && skippable(STAGES[index] as StageDef)) index += 1;
  return index;
}

/** Each stage with its state for this run. */
export function getStages(run: RunFields): StageView[] {
  const progress = Math.min(100, Math.max(0, run.progress));
  const skipped = (stage: StageDef) => Boolean(stage.needsLiveUrl) && !run.live_url;

  if (run.status === "succeeded") {
    return STAGES.map((stage) => ({ ...stage, state: skipped(stage) ? "skipped" : "done" }));
  }

  if (run.status === "queued") {
    return STAGES.map((stage) => ({ ...stage, state: skipped(stage) ? "skipped" : "pending" }));
  }

  if (run.status === "running") {
    const current = stageIndexAt(progress, skipped);
    return STAGES.map((stage, i) => ({
      ...stage,
      state: skipped(stage) ? "skipped" : i < current ? "done" : i === current ? "running" : "pending",
    }));
  }

  // Failed or cancelled. A run that never reached 5 percent never started a
  // stage, so none is blamed.
  const started = progress >= 5;
  const current = started ? stageIndexAt(progress, skipped) : -1;
  const stopped: StageState = run.status === "failed" ? "failed" : "not_run";
  return STAGES.map((stage, i) => ({
    ...stage,
    state: skipped(stage) ? "skipped" : i < current ? "done" : i === current ? stopped : "not_run",
  }));
}

/** The stage that is running, or that failed, if there is one. */
export function findStage(stages: StageView[], state: "running" | "failed"): StageView | undefined {
  return stages.find((stage) => stage.state === state);
}

/** "45 s", "3 min 12 s", "14 min" for a duration in milliseconds. */
export function formatDuration(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  if (total < 60) return `${total} s`;
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  if (minutes >= 10 || seconds === 0) return `${minutes} min`;
  return `${minutes} min ${seconds} s`;
}

/** Milliseconds between two ISO timestamps, or null when either is missing or unparseable. */
export function msBetween(from: string | null, to: string | number | null): number | null {
  if (!from || to === null) return null;
  const start = new Date(from).getTime();
  const end = typeof to === "number" ? to : new Date(to).getTime();
  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  return Math.max(0, end - start);
}

/** After this long running, the page says the audit is taking longer than usual. */
export const SLOW_RUN_MS = 3 * 60 * 1000;
