import { request, type Schemas } from "./api";
import type { JobTitle } from "./jobTitles";

export type UserRow = Schemas["UserRow"];
export type UserDetail = Schemas["UserDetail"];
export type HistoryEntry = Schemas["HistoryEntry"];

export interface NewUser { username: string; display_name: string; job_title: JobTitle }
export interface UserChange { job_title?: JobTitle; is_active?: boolean; reason?: string }

export const listUsers = () => request<UserRow[]>("/users");
export const fetchUser = (id: string) => request<UserDetail>(`/users/${id}`);
export const createUser = (user: NewUser) => request<UserRow>("/users", { method: "POST", body: JSON.stringify(user) });
export const changeUser = (id: string, change: UserChange) =>
  request<UserRow>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(change) });

export function formatWhen(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString("en-AU", { dateStyle: "medium", timeStyle: "short" }) : "Never";
}
