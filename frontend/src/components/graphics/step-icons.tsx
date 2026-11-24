import { GraphicIcon } from "@/components/graphics/icon";

/** Upload into a tray: add your code (a repo or a zip). */
export function CodeInIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <path d="M12 3v10" />
      <path d="m7 8 5 5 5-5" />
      <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </GraphicIcon>
  );
}

/** Magnifier with a check: the scan reads the code and probes the live app. */
export function ScanIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 5 5" />
      <path d="m8 10.5 1.8 1.8 3.2-3.6" />
    </GraphicIcon>
  );
}

/** Clipboard with a check: the Launch Report. */
export function ReportIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <rect x="6" y="4" width="12" height="17" rx="2" />
      <path d="M9 4a3 3 0 0 1 6 0" />
      <path d="m9 13 2 2 4-4" />
    </GraphicIcon>
  );
}
