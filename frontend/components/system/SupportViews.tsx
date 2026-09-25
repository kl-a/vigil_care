"use client";

import { formatDuration, formatIds, fetchQueueDepth, listJobs, listRefreshHistory, type JobView } from "@/lib/jobs";
import { listPipelineRuns } from "@/lib/system";
import { formatWhen } from "@/lib/users";
import { Check } from "./Check";
import { HEAD, IDS, RunStatus, SupportSection, TABLE, TD, TH, useSupportView } from "./parts";

/**
 * Support Views (#10, design doc §6.4): Jobs, the queue, pipeline runs and Refresh history. Open to every Job
 * Title, so they show IDs, Job Kinds, states, counts and timings only, never Patient data. Each reloads when
 * `version` changes.
 */

const shortId = (id: string) => id.slice(0, 8);
const scope = (systemWide: boolean) => (systemWide ? "System-wide" : "This Practice");
const steps = (job: JobView) =>
  job.steps.map((s) => [s.name, s.status === "succeeded" ? "✓" : "…", formatIds(s.output)].filter(Boolean).join(" ")).join(" · ");
const error = (job: JobView) => job.last_error && `${job.last_error}${job.status === "failed" ? ` after ${job.attempts} attempts` : ""}`;

export function QueueTile({ version }: { version: number }) {
  const { data: depth, error: failed } = useSupportView(fetchQueueDepth, version);
  if (failed) return <Check label="Job queue" value="Unknown" tone="neu" detail={failed} />;
  if (!depth) return <Check label="Job queue" value="Checking…" tone="neu" detail="" />;
  return (
    <Check
      label="Job queue"
      value={`${depth.queued} queued · ${depth.running} running`}
      tone={depth.failed_last_day > 0 ? "neg" : depth.running > 0 ? "cau" : "neu"}
      detail={depth.failed_last_day > 0 ? `${depth.failed_last_day} failed in the last day.` : "None failed in the last day."}
    />
  );
}

export function Jobs({ version }: { version: number }) {
  const { data: jobs, error: failed } = useSupportView(listJobs, version);
  return (
    <SupportSection
      id="jobs" title="Jobs" rows={jobs} error={failed}
      about="Background work, newest first: system-wide Jobs and this Practice's. IDs and counts only."
      empty="No Jobs yet."
    >
      {(rows) => (
        <table aria-label="Jobs" className={TABLE}>
          <thead className={HEAD}>
            <tr><th className={TH}>Job</th><th className={TH}>Job Kind</th><th className={TH}>Status</th><th className={TH}>Scope</th><th className={TH}>Queued</th><th className={TH}>Took</th><th className={TH}>Details</th></tr>
          </thead>
          <tbody>
            {rows.map((job) => (
              <tr key={job.id} className="border-t border-border">
                <td className={IDS} title={job.id}>{shortId(job.id)}</td>
                <td className={`${TD} font-mono text-xs`}>{job.kind}</td>
                <td className={TD}><RunStatus status={job.status} /></td>
                <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{scope(job.system_wide)}</td>
                <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{formatWhen(job.created_at)}</td>
                <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{formatDuration(job.created_at, job.finished_at)}</td>
                <td className={IDS}>
                  {[formatIds(job.payload), steps(job)].filter(Boolean).join(" · ")}
                  {job.last_error && <div className="text-neg">{error(job)}</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </SupportSection>
  );
}

export function RefreshHistory({ version }: { version: number }) {
  const { data: history, error: failed } = useSupportView(listRefreshHistory, version);
  return (
    <SupportSection
      id="refresh-history" title="Refresh history" rows={history} error={failed}
      about="Every Refresh, newest first, with what it stored."
      empty="No Refresh has run yet."
    >
      {(rows) => (
        <table aria-label="Refresh history" className={TABLE}>
          <thead className={HEAD}>
            <tr><th className={TH}>Refresh</th><th className={TH}>Status</th><th className={TH}>Started</th><th className={TH}>Took</th><th className={TH}>Result</th></tr>
          </thead>
          <tbody>
            {rows.map((job) => (
              <tr key={job.id} className="border-t border-border">
                <td className={`${TD} font-mono text-xs`}>{job.kind}</td>
                <td className={TD}><RunStatus status={job.status} /></td>
                <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{formatWhen(job.created_at)}</td>
                <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{formatDuration(job.created_at, job.finished_at)}</td>
                <td className={IDS}>
                  {formatIds(Object.assign({}, ...job.steps.map((s) => s.output)))}
                  {job.last_error && <div className="text-neg">{error(job)}</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </SupportSection>
  );
}

export function PipelineRuns({ version }: { version: number }) {
  const { data: runs, error: failed } = useSupportView(listPipelineRuns, version);
  return (
    <SupportSection
      id="pipeline-runs" title="Pipeline runs" rows={runs} error={failed}
      about="Each run of a pipeline, newest first: its status, timings and error code. IDs only."
      empty="No pipeline runs yet. They start with document processing (Stage 8)."
    >
      {(rows) => (
        <table aria-label="Pipeline runs" className={TABLE}>
          <thead className={HEAD}>
            <tr><th className={TH}>Run</th><th className={TH}>Kind</th><th className={TH}>Status</th><th className={TH}>Scope</th><th className={TH}>Started</th><th className={TH}>Took</th><th className={TH}>Inputs</th><th className={TH}>Error</th></tr>
          </thead>
          <tbody>
            {rows.map((run) => (
              <tr key={run.id} className="border-t border-border">
                <td className={IDS} title={run.id}>{shortId(run.id)}</td>
                <td className={`${TD} font-mono text-xs`}>{run.kind}</td>
                <td className={TD}><RunStatus status={run.status} /></td>
                <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{scope(run.system_wide)}</td>
                <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{formatWhen(run.started_at)}</td>
                <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{formatDuration(run.started_at, run.finished_at)}</td>
                <td className={IDS}>{formatIds(run.inputs)}</td>
                <td className="px-3 py-2 align-top font-mono text-xs text-neg">{run.error_detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </SupportSection>
  );
}
