import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearSessionToken,
  getSessionToken,
  SESSION_CHANGED_EVENT,
  SESSION_STORAGE_KEY,
  setSessionToken,
} from "@/lib/session";

beforeEach(() => {
  window.localStorage.clear();
});

describe("session token storage", () => {
  it("returns null when nothing is stored", () => {
    expect(getSessionToken()).toBeNull();
  });

  it("round-trips a stored token", () => {
    setSessionToken("token-123");
    expect(getSessionToken()).toBe("token-123");
    expect(window.localStorage.getItem(SESSION_STORAGE_KEY)).toBe("token-123");
  });

  it("dispatches a change event when a token is stored", () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_CHANGED_EVENT, listener);
    setSessionToken("token-123");
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener(SESSION_CHANGED_EVENT, listener);
  });

  it("clears the token and dispatches a change event", () => {
    setSessionToken("token-123");
    const listener = vi.fn();
    window.addEventListener(SESSION_CHANGED_EVENT, listener);
    clearSessionToken();
    expect(getSessionToken()).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener(SESSION_CHANGED_EVENT, listener);
  });
});
