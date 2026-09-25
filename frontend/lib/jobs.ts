import { request, type Schemas } from "./api";

export type JobView = Schemas["JobView"];
export type RefreshView = Schemas["RefreshView"];

export const listRefreshes = () => request<RefreshView[]>("/refreshes");
export const startRefresh = (kind: string) => request<JobView>("/refreshes", { method: "POST", body: JSON.stringify({ kind }) });
export const fetchJob = (id: string) => request<JobView>(`/jobs/${id}`);

/** A Job still waiting or running, so worth watching. */
export const isActive = (job: JobView | null | undefined) => job?.status === "queued" || job?.status === "running";
