import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

/**
 * A line of code to paste somewhere, with a copy button. The copy is
 * announced to assistive tech; without the clipboard API the text is
 * selected instead so people can copy it themselves.
 */
export function CopySnippet({
  id,
  label,
  value,
  copyLabel,
  disabled,
}: {
  id: string;
  /** What the snippet is, e.g. "Tag for your home page". */
  label: string;
  value: string;
  /** Button text, e.g. "Copy tag". */
  copyLabel: string;
  disabled?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    },
    [],
  );

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      const node = codeRef.current;
      const selection = window.getSelection();
      if (!node || !selection) return;
      const range = document.createRange();
      range.selectNodeContents(node);
      selection.removeAllRanges();
      selection.addRange(range);
    }
    setCopied(true);
    if (timerRef.current !== null) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex flex-col gap-1.5">
      <p id={`${id}-label`} className="text-[0.8125rem] font-medium text-foreground">
        {label}
      </p>
      <div className="flex items-stretch gap-2">
        <code
          ref={codeRef}
          aria-labelledby={`${id}-label`}
          className="flex min-h-9 min-w-0 flex-1 items-center overflow-x-auto rounded-[10px] border border-border bg-sunken px-3 py-1.5 font-mono text-xs whitespace-nowrap text-foreground"
        >
          {value}
        </code>
        <Button
          type="button"
          variant="outline"
          onClick={() => void copy()}
          disabled={disabled}
          aria-describedby={`${id}-label`}
          className="h-auto min-h-9 min-w-24"
        >
          {copied ? (
            <>
              <Check aria-hidden="true" className="size-4" />
              Copied
            </>
          ) : (
            <>
              <Copy aria-hidden="true" className="size-4" />
              {copyLabel}
            </>
          )}
        </Button>
      </div>
      <p aria-live="polite" className="sr-only">
        {copied ? `${label} copied to the clipboard.` : ""}
      </p>
    </div>
  );
}
