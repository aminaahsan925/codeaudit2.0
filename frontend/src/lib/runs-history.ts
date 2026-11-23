import { z } from "zod";

/*
  Run history lives in the browser, not the API: GET /api/runs needs a
  bearer token and this build has no login UI, so the history page lists
  the runs this browser created, stored at creation time. A run stays
  reachable from its link even on a browser that never stored it.
*/

export const RUNS_STORAGE_KEY = "launchaudit:runs:v1";
export const MAX_STORED_RUNS = 50;

/** Dispatched on window after this tab writes the history. */
const RUNS_CHANGED_EVENT = "launchaudit:runs-changed";

export interface StoredRun {
  id: string;
  projectName: string;
  /** ISO timestamp of creation, used to order the history newest first. */
  createdAt: string;
}

const storedRunSchema = z.object({
  id: z.string().min(1).max(64),
  projectName: z.string().min(1).max(200),
  createdAt: z.string().min(1).max(64),
});

const storedRunsSchema = z.array(storedRunSchema).max(MAX_STORED_RUNS);

function parseStoredRuns(raw: string | null): StoredRun[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    const result = storedRunsSchema.safeParse(parsed);
    return result.success ? result.data : [];
  } catch {
    return [];
  }
}

function readStorage(): StoredRun[] {
  if (typeof window === "undefined") return [];
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(RUNS_STORAGE_KEY);
  } catch {
    return [];
  }
  return parseStoredRuns(raw);
}

function writeStorage(runs: StoredRun[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(RUNS_STORAGE_KEY, JSON.stringify(runs));
  } catch {
    // Storage full or unavailable: history is a convenience, never fatal.
  }
  window.dispatchEvent(new Event(RUNS_CHANGED_EVENT));
}

/*
  Cached snapshot for useSyncExternalStore: the snapshot must keep the
  same reference while the stored value is unchanged, or React re-renders
  in a loop. The cache keys on the raw stored string.
*/
let cachedRaw: string | null | undefined;
let cachedRuns: StoredRun[] = [];

/** Current stored runs (newest first), reference-stable while unchanged. */
export function getStoredRunsSnapshot(): StoredRun[] {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(RUNS_STORAGE_KEY);
  } catch {
    raw = null;
  }
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cachedRuns = parseStoredRuns(raw).sort((a, b) =>
      b.createdAt.localeCompare(a.createdAt),
    );
  }
  return cachedRuns;
}

const EMPTY_STORED_RUNS: StoredRun[] = [];

/** The server snapshot: no storage on the server, so no runs. */
export function getStoredRunsServerSnapshot(): StoredRun[] {
  return EMPTY_STORED_RUNS;
}

/** Notifies subscribers when the history changes in this tab or another. */
export function subscribeToStoredRuns(onChange: () => void): () => void {
  const onStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === RUNS_STORAGE_KEY) onChange();
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener(RUNS_CHANGED_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(RUNS_CHANGED_EVENT, onChange);
  };
}

/** Stored runs, newest first. Corrupt or missing storage reads as empty. */
export function loadStoredRuns(): StoredRun[] {
  return readStorage().sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

/** Records a run at creation time (also used for reruns). Returns the new list. */
export function recordRun(run: { id: string; projectName: string }): StoredRun[] {
  const entry: StoredRun = {
    id: run.id,
    projectName: run.projectName,
    createdAt: new Date().toISOString(),
  };
  const next = [entry, ...readStorage().filter((item) => item.id !== entry.id)].slice(
    0,
    MAX_STORED_RUNS,
  );
  writeStorage(next);
  return loadStoredRuns();
}

/** Drops one run from this browser's history. Returns the new list. */
export function removeStoredRun(id: string): StoredRun[] {
  const next = readStorage().filter((item) => item.id !== id);
  writeStorage(next);
  return loadStoredRuns();
}
