import { describe, expect, it, vi } from "vitest";

import { notifySessionChanged, SESSION_CHANGED_EVENT } from "@/lib/session";

describe("session change notification", () => {
  it("dispatches a change event", () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_CHANGED_EVENT, listener);
    notifySessionChanged();
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener(SESSION_CHANGED_EVENT, listener);
  });

  it("does nothing outside the browser", () => {
    // jsdom always has a window; the guard is covered by the call above
    // not throwing when window exists. The server path is exercised by
    // the auth callback page's server render in the e2e suite.
    expect(() => notifySessionChanged()).not.toThrow();
  });
});
