import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useReport, useSharedReport } from "@/hooks/use-report";
import { useRun, RUN_POLL_INTERVAL_MS } from "@/hooks/use-run";
import { useRunsHistory } from "@/hooks/use-runs-history";
import { RUNS_STORAGE_KEY } from "@/lib/runs-history";

import { makeReport, makeRun, RUN_ID, SHARE_TOKEN } from "./fixtures";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubFetch(impl: (req: Request) => Promise<Response>) {
  const fn = vi.fn(impl);
  vi.stubGlobal("fetch", fn);
  return fn;
}

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("useRun", () => {
  it("fetches the run once when it is already finished", async () => {
    const fetchMock = stubFetch(async () => json(makeRun({ status: "succeeded" })));
    const { result } = renderHook(() => useRun(RUN_ID), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("succeeded");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("polls while running and stops once the run succeeds", async () => {
    vi.useFakeTimers();
    let status: "running" | "succeeded" = "running";
    const fetchMock = stubFetch(async () => json(makeRun({ status })));

    // Timer advances are wrapped in act so React flushes the query's
    // state updates after each refetch resolves.
    const advance = (ms: number) =>
      act(async () => {
        await vi.advanceTimersByTimeAsync(ms);
      });

    const { result } = renderHook(() => useRun(RUN_ID), { wrapper: makeWrapper() });
    await advance(0);
    expect(result.current.data?.status).toBe("running");

    await advance(RUN_POLL_INTERVAL_MS);
    await advance(RUN_POLL_INTERVAL_MS);
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(3);

    status = "succeeded";
    await advance(RUN_POLL_INTERVAL_MS);
    // The refetch that returns "succeeded" fires at the interval edge; the
    // query state update lands one timer cycle later.
    await advance(RUN_POLL_INTERVAL_MS);
    expect(result.current.data?.status).toBe("succeeded");
    const callsAfterSuccess = fetchMock.mock.calls.length;

    await advance(RUN_POLL_INTERVAL_MS * 5);
    expect(fetchMock.mock.calls.length).toBe(callsAfterSuccess);
  });

  it("surfaces a 404 as an error", async () => {
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Audit run not found." } }, 404),
    );
    const { result } = renderHook(() => useRun(RUN_ID), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.code).toBe("not_found");
  });

  it("does not fetch without a run id", async () => {
    const fetchMock = stubFetch(async () => json(makeRun()));
    renderHook(() => useRun(null), { wrapper: makeWrapper() });
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("useReport", () => {
  it("loads the run, then the report through its share token", async () => {
    const fetchMock = stubFetch(async (req) => {
      const path = new URL(req.url).pathname;
      if (path === `/api/runs/${RUN_ID}`) return json(makeRun());
      if (path === `/api/reports/shared/${SHARE_TOKEN}`) return json(makeReport());
      return json({ error: { code: "not_found", message: "Nope." } }, 404);
    });

    const { result } = renderHook(() => useReport(RUN_ID), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.run.id).toBe(RUN_ID);
    expect(result.current.data?.findings).toHaveLength(1);
    expect(fetchMock.mock.calls.map(([req]) => new URL(req.url).pathname)).toEqual([
      `/api/runs/${RUN_ID}`,
      `/api/reports/shared/${SHARE_TOKEN}`,
    ]);
  });

  it("errors when the run has no share token", async () => {
    stubFetch(async () => json(makeRun({ share_token: null })));
    const { result } = renderHook(() => useReport(RUN_ID), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toMatch(/no share link/);
  });
});

describe("useSharedReport", () => {
  it("loads the report by token", async () => {
    stubFetch(async () => json(makeReport()));
    const { result } = renderHook(() => useSharedReport(SHARE_TOKEN), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.run.project_name).toBe("pocket-notes");
  });
});

describe("useRunsHistory", () => {
  it("enriches stored runs with their live status", async () => {
    window.localStorage.setItem(
      RUNS_STORAGE_KEY,
      JSON.stringify([
        { id: RUN_ID, projectName: "pocket-notes", createdAt: "2026-11-24T00:00:00Z" },
      ]),
    );
    stubFetch(async () => json(makeRun()));
    const { result } = renderHook(() => useRunsHistory(), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.entries).toHaveLength(1));
    await waitFor(() =>
      expect(result.current.entries?.[0]?.run?.status).toBe("succeeded"),
    );
    expect(result.current.entries?.[0]?.stored.projectName).toBe("pocket-notes");
  });

  it("marks an entry as errored when its run cannot be loaded", async () => {
    window.localStorage.setItem(
      RUNS_STORAGE_KEY,
      JSON.stringify([
        { id: RUN_ID, projectName: "pocket-notes", createdAt: "2026-11-24T00:00:00Z" },
      ]),
    );
    stubFetch(async () =>
      json({ error: { code: "not_found", message: "Audit run not found." } }, 404),
    );
    const { result } = renderHook(() => useRunsHistory(), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.entries?.[0]?.isError).toBe(true));
    expect(result.current.entries?.[0]?.run).toBeUndefined();
  });

  it("returns an empty list when nothing is stored", async () => {
    const { result } = renderHook(() => useRunsHistory(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.entries).toEqual([]));
  });
});
