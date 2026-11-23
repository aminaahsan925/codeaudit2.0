"use client";

import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** The page origin, resolved after hydration (empty during server render). */
function useOrigin(): string {
  return useSyncExternalStore(
    () => () => {},
    () => window.location.origin,
    () => "",
  );
}

/**
 * A copyable share link: the URL in a readonly field plus a copy button.
 * The button falls back to selecting the field when the clipboard API is
 * unavailable, and announces the copy to assistive tech.
 */
export function ShareLink({
  path,
  label = "Share link",
  className,
}: {
  /** Frontend path, e.g. `/r/<token>`; the origin is added in the browser. */
  path: string;
  label?: string;
  className?: string;
}) {
  const origin = useOrigin();
  const url = `${origin}${path}`;
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    },
    [],
  );

  async function copy() {
    let done = false;
    try {
      await navigator.clipboard.writeText(url);
      done = true;
    } catch {
      const input = inputRef.current;
      if (input) {
        input.select();
        done = true;
      }
    }
    if (done) {
      setCopied(true);
      if (timerRef.current !== null) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor="share-link-input" className="text-sm font-medium">
        {label}
      </label>
      <div className="flex gap-2">
        <input
          ref={inputRef}
          id="share-link-input"
          type="text"
          readOnly
          value={url}
          onFocus={(event) => event.currentTarget.select()}
          className="h-9 min-w-0 flex-1 rounded-md border border-input bg-muted px-3 font-mono text-xs text-muted-foreground outline-none"
        />
        <Button type="button" variant="outline" onClick={() => void copy()}>
          {copied ? (
            <>
              <Check aria-hidden="true" className="size-4" />
              Copied
            </>
          ) : (
            <>
              <Copy aria-hidden="true" className="size-4" />
              Copy link
            </>
          )}
        </Button>
      </div>
      <p aria-live="polite" className="sr-only">
        {copied ? "Share link copied to the clipboard." : ""}
      </p>
      <p className="text-xs text-muted-foreground">
        Anyone with this link can read the report. No account needed.
      </p>
    </div>
  );
}
