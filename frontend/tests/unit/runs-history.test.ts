import { beforeEach, describe, expect, it } from "vitest";

import {
  loadStoredRuns,
  recordRun,
  removeStoredRun,
  RUNS_STORAGE_KEY,
} from "@/lib/runs-history";

beforeEach(() => {
  window.localStorage.clear();
});

describe("loadStoredRuns", () => {
  it("reads empty storage as an empty list", () => {
    expect(loadStoredRuns()).toEqual([]);
  });

  it("reads corrupt storage as an empty list", () => {
    window.localStorage.setItem(RUNS_STORAGE_KEY, "{not json");
    expect(loadStoredRuns()).toEqual([]);
  });

  it("reads malformed entries as an empty list", () => {
    window.localStorage.setItem(
      RUNS_STORAGE_KEY,
      JSON.stringify([{ id: 42, projectName: "x" }]),
    );
    expect(loadStoredRuns()).toEqual([]);
  });

  it("orders stored runs newest first", () => {
    window.localStorage.setItem(
      RUNS_STORAGE_KEY,
      JSON.stringify([
        { id: "old", projectName: "Old", createdAt: "2026-11-20T00:00:00Z" },
        { id: "new", projectName: "New", createdAt: "2026-11-24T00:00:00Z" },
      ]),
    );
    expect(loadStoredRuns().map((run) => run.id)).toEqual(["new", "old"]);
  });
});

describe("recordRun", () => {
  it("stores a run and returns it first", () => {
    const runs = recordRun({ id: "abc", projectName: "pocket-notes" });
    expect(runs).toHaveLength(1);
    expect(runs[0]).toMatchObject({ id: "abc", projectName: "pocket-notes" });
    expect(loadStoredRuns()).toEqual(runs);
  });

  it("re-recording the same run keeps one entry", () => {
    recordRun({ id: "abc", projectName: "pocket-notes" });
    const runs = recordRun({ id: "abc", projectName: "pocket-notes" });
    expect(runs).toHaveLength(1);
  });
});

describe("removeStoredRun", () => {
  it("drops only the named run", () => {
    recordRun({ id: "a", projectName: "A" });
    recordRun({ id: "b", projectName: "B" });
    const runs = removeStoredRun("a");
    expect(runs.map((run) => run.id)).toEqual(["b"]);
  });
});
