import { request, type Schemas } from "./api";

export type SiteRow = Schemas["SiteRow"];
export type NewSite = Schemas["NewSite"];
export type SiteChange = Schemas["SiteChange"];

export const listSites = () => request<SiteRow[]>("/sites");
export const addSite = (site: NewSite) => request<SiteRow>("/sites", { method: "POST", body: JSON.stringify(site) });
export const changeSite = (id: string, change: SiteChange) =>
  request<SiteRow>(`/sites/${id}`, { method: "PATCH", body: JSON.stringify(change) });
export const deleteSite = (id: string, reason: string) =>
  request<void>(`/sites/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });
