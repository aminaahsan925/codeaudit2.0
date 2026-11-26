"use client";

import { useEffect, useState } from "react";

/*
  Small, dependency-free number animation for scores. Using requestAnimationFrame
  directly keeps the motion library's full animation engine out of the
  first-load bundle (only `m` components and lazily loaded features ship).
*/

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

/**
 * Animates from `from` to `to` over `durationMs` once `start` is true.
 * Before starting it holds `initial`; with reduced motion it jumps to `to`.
 */
export function useCountUp({
  from,
  to,
  durationMs,
  start,
  initial = to,
  delayMs = 0,
}: {
  from: number;
  to: number;
  durationMs: number;
  start: boolean;
  initial?: number;
  delayMs?: number;
}): number {
  const [value, setValue] = useState(initial);

  useEffect(() => {
    if (!start) return;
    let frame = 0;
    let timer = 0;
    const run = () => {
      if (prefersReducedMotion()) {
        frame = requestAnimationFrame(() => setValue(to));
        return;
      }
      const t0 = performance.now();
      const step = (now: number) => {
        const t = Math.min(1, (now - t0) / durationMs);
        setValue(from + (to - from) * easeOut(t));
        if (t < 1) frame = requestAnimationFrame(step);
      };
      frame = requestAnimationFrame(step);
    };
    timer = window.setTimeout(run, delayMs);
    return () => {
      window.clearTimeout(timer);
      cancelAnimationFrame(frame);
    };
  }, [start, from, to, durationMs, delayMs]);

  return value;
}

/**
 * Imperative variant for values written straight to the DOM (no re-render per
 * frame). Calls `onFrame` with each value; returns a cancel function.
 */
export function animateNumber(
  from: number,
  to: number,
  durationMs: number,
  onFrame: (value: number) => void,
): () => void {
  if (prefersReducedMotion()) {
    onFrame(to);
    return () => {};
  }
  let frame = 0;
  const t0 = performance.now();
  const step = (now: number) => {
    const t = Math.min(1, (now - t0) / durationMs);
    onFrame(from + (to - from) * easeOut(t));
    if (t < 1) frame = requestAnimationFrame(step);
  };
  frame = requestAnimationFrame(step);
  return () => cancelAnimationFrame(frame);
}
