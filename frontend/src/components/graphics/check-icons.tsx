import { GraphicIcon } from "@/components/graphics/icon";

/** Key: leaked secrets (API keys, tokens, passwords). */
export function KeyIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <circle cx="7.5" cy="15.5" r="4.5" />
      <path d="m11 12 9-9" />
      <path d="m15.5 7.5 2 2" />
      <path d="m18 5 2 2" />
    </GraphicIcon>
  );
}

/** Angle brackets: injection (input reaching a query, shell or template). */
export function InjectionIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <path d="m8 6-5 6 5 6" />
      <path d="m16 6 5 6-5 6" />
      <path d="M13 4l-2 16" />
    </GraphicIcon>
  );
}

/** Padlock: login and access control. */
export function LockIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
      <circle cx="12" cy="15.5" r="1" fill="currentColor" stroke="none" />
    </GraphicIcon>
  );
}

/** Package: vulnerable dependencies. */
export function PackageIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <path d="M12 2 21 7v10l-9 5-9-5V7Z" />
      <path d="m3 7 9 5 9-5" />
      <path d="M12 12v10" />
    </GraphicIcon>
  );
}

/** Globe: live configuration (headers, CORS, exposed files, debug pages). */
export function GlobeIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a13.5 13.5 0 0 1 0 18" />
      <path d="M12 3a13.5 13.5 0 0 0 0 18" />
    </GraphicIcon>
  );
}

/** Shield with angle brackets: request forgery and XSS. */
export function ShieldScriptIcon({ className }: { className?: string }) {
  return (
    <GraphicIcon className={className}>
      <path d="M12 2 20 5v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V5Z" />
      <path d="m9.5 9.5-2 2.5 2 2.5" />
      <path d="m14.5 9.5 2 2.5-2 2.5" />
    </GraphicIcon>
  );
}
