import { request, type Schemas } from "./api";

export type JobView = Schemas["JobView"];
export type RefreshView = Schemas["RefreshView"];
export type QueueDepth = Schemas["QueueDepthView"];

export const listRefreshes = () => request<RefreshView[]>("/refreshes");
export const listRefreshHistory = () => request<JobView[]>("/refreshes/history");
export const startRefresh = (kind: string) => request<JobView>("/refreshes", { method: "POST", body: JSON.stringify({ kind }) });
export const fetchJob = (id: string) => request<JobView>(`/jobs/${id}`);
export const listJobs = () => request<JobView[]>("/jobs");
export const fetchQueueDepth = () => request<QueueDepth>("/queue");

/** A Job still waiting or running, so worth watching. */
export const isActive = (job: JobView | null | undefined) => job?.status === "queued" || job?.status === "running";

/** IDs-only values (payloads, step outputs, pipeline-run inputs) as "key=value · key=value". */
export function formatIds(values: Record<string, unknown>): string {
  return Object.entries(values)
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join(",") : String(value)}`)
    .join(" · ");
}

/** How long something took: "42 s", "3 min 5 s", "1 h 4 min". Empty until it has finished. */
export function formatDuration(start: string | null | undefined, end: string | null | undefined): string {
  if (!start || !end) return "";
  const seconds = Math.max(0, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000));
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return seconds % 60 ? `${minutes} min ${seconds % 60} s` : `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}
