import { CalendarDays, Code2, Eye, Globe } from "lucide-react";

import type { AuditRun } from "@/lib/api";
import { formatDateTime } from "@/lib/dates";

/**
 * Project name and what this audit covered: when, which code, which site.
 * The shared view adds a "Shared report, read only" note.
 */
export function ReportHeader({ run, readOnly = false }: { run: AuditRun; readOnly?: boolean }) {
  const runDate = formatDateTime(run.finished_at ?? run.started_at);
  return (
    <header className="flex min-w-0 flex-col gap-2.5">
      <h1 className="text-3xl leading-tight text-balance break-words sm:text-[2.5rem] sm:leading-[1.1]">
        {run.project_name}
      </h1>
      <ul className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm text-muted-foreground">
        {readOnly ? (
          <li className="flex items-center gap-1.5 font-medium text-foreground">
            <Eye aria-hidden="true" className="size-4 shrink-0" />
            Shared report, read only
          </li>
        ) : null}
        {runDate ? (
          <li className="flex items-center gap-1.5">
            <CalendarDays aria-hidden="true" className="size-4 shrink-0" />
            <span>
              <span className="sr-only">Audited on </span>
              {runDate}
            </span>
          </li>
        ) : null}
        <li className="flex min-w-0 items-center gap-1.5">
          <Code2 aria-hidden="true" className="size-4 shrink-0" />
          {run.repo_url ? (
            <span className="min-w-0 truncate font-mono text-xs">
              <span className="sr-only">Code from </span>
              {run.repo_url.replace(/^https?:\/\//, "")}
            </span>
          ) : (
            <span>Code from an uploaded zip</span>
          )}
        </li>
        <li className="flex min-w-0 items-center gap-1.5">
          <Globe aria-hidden="true" className="size-4 shrink-0" />
          {run.live_url ? (
            <span className="min-w-0 truncate font-mono text-xs">
              <span className="sr-only">Live site </span>
              {run.live_url.replace(/^https?:\/\//, "")}
            </span>
          ) : (
            <span>No live site checked</span>
          )}
        </li>
      </ul>
    </header>
  );
}
