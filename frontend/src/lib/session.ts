/**
 * Signed-in session token, kept in localStorage so a refresh keeps the user
 * signed in. The token is sent as an Authorization: Bearer header on API
 * calls (see lib/api/client.ts). Every change dispatches an event so hooks
 * in the same tab can react; cross-tab changes arrive via the storage event.
 */

export const SESSION_STORAGE_KEY = "launchaudit:session:v1";

export const SESSION_CHANGED_EVENT = "launchaudit:session-changed";

export function getSessionToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setSessionToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(SESSION_STORAGE_KEY, token);
  } catch {
    // Storage full or blocked: the session just won't survive a refresh.
  }
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

export function clearSessionToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // Nothing to do: the token is already gone or storage is unusable.
  }
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}
