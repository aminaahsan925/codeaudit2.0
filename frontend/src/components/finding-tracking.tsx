"use client";

import { useState } from "react";

import { useUpdateFinding } from "@/hooks/use-findings";
import { isApiError, type Finding } from "@/lib/api";
import { TRACKING_STATUSES, TRACKING_STATUS_LABEL } from "@/lib/report";

const inputClasses =
  "h-9 w-full rounded-md border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

/**
 * Assign and track one finding: who owns the fix, and where it stands.
 * The assignee saves on blur or Enter; the status saves as soon as it
 * changes. On the public shared report (`readOnly`) the same information
 * shows as plain text with no controls, since that route has no auth.
 * The editor lives in its own component so the read-only view never calls
 * the mutation hook (and never needs a QueryClient).
 */
export function FindingTracking({
  finding,
  runId,
  readOnly = false,
}: {
  finding: Finding;
  runId: string;
  readOnly?: boolean;
}) {
  if (readOnly) {
    return (
      <p className="text-xs text-muted-foreground">
        {finding.assignee ? `Assigned to ${finding.assignee}` : "Unassigned"}
        {" · "}
        {TRACKING_STATUS_LABEL[finding.tracking_status]}
      </p>
    );
  }
  return <FindingTrackingEditor finding={finding} runId={runId} />;
}

function FindingTrackingEditor({
  finding,
  runId,
}: {
  finding: Finding;
  runId: string;
}) {
  const update = useUpdateFinding(runId);
  const [assignee, setAssignee] = useState(finding.assignee ?? "");
  const [saveError, setSaveError] = useState<string | null>(null);

  // Keep the input in step with the finding: when the assignee changes
  // from outside (optimistic update, rollback, refetch), adopt it. The
  // render-time adjustment below is the React-recommended pattern for
  // this; typing never changes the prop, so it never clobbers an edit.
  // prevAssignee keeps the raw value (null included) so the comparison
  // settles instead of re-adjusting on every render.
  const [prevAssignee, setPrevAssignee] = useState(finding.assignee);
  if (finding.assignee !== prevAssignee) {
    setPrevAssignee(finding.assignee);
    setAssignee(finding.assignee ?? "");
  }

  const assigneeId = `finding-assignee-${finding.id}`;
  const statusId = `finding-status-${finding.id}`;
  const saving = update.isPending;

  function saveAssignee() {
    const trimmed = assignee.trim();
    const current = finding.assignee ?? "";
    if (trimmed === current) return;
    setSaveError(null);
    update.mutate(
      { findingId: finding.id, payload: { assignee: trimmed ? trimmed : null } },
      {
        onError: (error) => {
          setSaveError(
            isApiError(error) ? error.message : "The assignment could not be saved.",
          );
        },
      },
    );
  }

  function saveStatus(status: string) {
    if (status === finding.tracking_status) return;
    setSaveError(null);
    update.mutate(
      { findingId: finding.id, payload: { tracking_status: status } },
      {
        onError: (error) => {
          setSaveError(
            isApiError(error) ? error.message : "The status could not be saved.",
          );
        },
      },
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex min-w-44 flex-1 flex-col gap-1">
          <label htmlFor={assigneeId} className="text-xs font-medium text-muted-foreground">
            Assigned to
          </label>
          <input
            id={assigneeId}
            type="text"
            autoComplete="off"
            maxLength={200}
            placeholder="Name or email"
            value={assignee}
            disabled={saving}
            onChange={(event) => setAssignee(event.target.value)}
            onBlur={() => saveAssignee()}
            onKeyDown={(event) => {
              if (event.key === "Enter") event.currentTarget.blur();
            }}
            className={inputClasses}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor={statusId} className="text-xs font-medium text-muted-foreground">
            Status
          </label>
          <select
            id={statusId}
            value={finding.tracking_status}
            disabled={saving}
            onChange={(event) => saveStatus(event.target.value)}
            className={inputClasses}
          >
            {TRACKING_STATUSES.map((status) => (
              <option key={status} value={status}>
                {TRACKING_STATUS_LABEL[status]}
              </option>
            ))}
          </select>
        </div>
        {saving ? (
          <span className="pb-2 text-xs text-muted-foreground">Saving…</span>
        ) : null}
      </div>
      {saveError ? (
        <p role="alert" className="text-xs text-sev-critical-fg">
          {saveError}
        </p>
      ) : null}
    </div>
  );
}
