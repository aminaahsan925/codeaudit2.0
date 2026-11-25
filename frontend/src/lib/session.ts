/**
 * Session change notification. The session token itself lives in an
 * HttpOnly cookie the browser sends with every API call, so JavaScript
 * never holds it: no code here reads, stores or sends the token. This event
 * lets hooks in the same tab react when sign-in or sign-out happens.
 */

export const SESSION_CHANGED_EVENT = "launchaudit:session-changed";

export function notifySessionChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}
