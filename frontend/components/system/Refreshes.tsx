"use client";

import { useCallback, useEffect, useState } from "react";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { StatusPill, type Tone } from "@/components/ui/StatusPill";
import { messageOf } from "@/lib/api";
import { fetchJob, isActive, listRefreshes, startRefresh, type JobView, type RefreshView } from "@/lib/jobs";
import { formatWhen } from "@/lib/users";

const POLL_MS = 1000;
const STATUS: Record<string, { label: string; tone: Tone }> = {
  queued: { label: "Queued", tone: "neu" },
  running: { label: "Running", tone: "cau" },
  succeeded: { label: "Succeeded", tone: "pos" },
  failed: { label: "Failed", tone: "neg" },
  cancelled: { label: "Cancelled", tone: "neu" },
};

/**
 * Refreshes (#18, design doc §6.4): the last run of each, for everyone; only a developer admin starts one.
 * A started Refresh is followed until it finishes. IDs, states and error codes only.
 */
export function Refreshes() {
  const me = useSignedInUser();
  const canStart = me.job_title === "developer_admin";
  const [refreshes, setRefreshes] = useState<RefreshView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    listRefreshes().then(setRefreshes).catch((reason: unknown) => setError(messageOf(reason)));
  }, []);
  useEffect(load, [load]);

  return (
    <section aria-labelledby="refreshes" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <h2 id="refreshes" className="m-0 text-sm font-semibold">Refreshes</h2>
      <p className="m-0 max-w-[70ch] text-[13px] text-muted-foreground">Vigil keeps its own copies of public data, refreshed on a schedule by the worker.</p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {refreshes === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {refreshes && (
        <ul aria-label="Refreshes" className="m-0 flex list-none flex-col gap-2 p-0">
          {refreshes.map((refresh) => <RefreshItem key={refresh.kind} refresh={refresh} canStart={canStart} />)}
        </ul>
      )}
      {!canStart && <p className="m-0 text-xs text-muted-foreground">Only a developer admin starts a Refresh.</p>}
    </section>
  );
}

function RefreshItem({ refresh, canStart }: { refresh: RefreshView; canStart: boolean }) {
  const [job, setJob] = useState<JobView | null>(refresh.last_job ?? null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || !isActive(job)) return;
    const timer = setTimeout(() => {
      fetchJob(job.id).then(setJob).catch((reason: unknown) => setError(messageOf(reason)));
    }, POLL_MS);
    return () => clearTimeout(timer);
  }, [job]);

  async function start() {
    setError(null);
    try {
      setJob(await startRefresh(refresh.kind));
    } catch (reason) {
      setError(messageOf(reason));
    }
  }

  const status = job ? STATUS[job.status] ?? { label: job.status, tone: "neu" as Tone } : null;
  return (
    <li className="flex flex-col gap-1.5 rounded-md border border-border px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-[13px] font-medium">{refresh.description}</span>
        <span className="flex items-center gap-2">
          {status ? <StatusPill tone={status.tone}>{status.label}</StatusPill> : <span className="text-xs text-muted-foreground">Never run</span>}
          {canStart && (
            <button onClick={start} disabled={isActive(job)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted disabled:opacity-50">
              Start Refresh
            </button>
          )}
        </span>
      </div>
      {job && (
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
          <span>Started {formatWhen(job.created_at)}</span>
          {job.finished_at && <span>Finished {formatWhen(job.finished_at)}</span>}
          {job.steps.length > 0 && <span className="font-mono">{job.steps.map((s) => `${s.name} ${s.status === "succeeded" ? "✓" : "…"}`).join(" · ")}</span>}
          {job.last_error && (
            <span className="font-mono text-neg">{job.last_error}{job.status === "failed" ? ` after ${job.attempts} attempts` : ""}</span>
          )}
        </div>
      )}
      {error && <p role="alert" className="m-0 text-xs text-neg">{error}</p>}
    </li>
  );
}
