import { request, type Schemas } from "@/lib/api";
import type { ModuleKey } from "./types";

export type ActiveConfiguration = Schemas["ActiveConfiguration"];
export type ModuleStatus = Schemas["ModuleStatus"];

/** The Specialty Modules active for the signed-in User's Practice (per-Practice activation, #15). */
export async function fetchActiveModules(): Promise<ModuleKey[]> {
  return (await request<ActiveConfiguration>("/modules/active")).active_modules;
}

export const listModules = () => request<ModuleStatus[]>("/modules");
export const setModuleActive = (key: string, change: { is_active: boolean; reason?: string }) =>
  request<ModuleStatus>(`/modules/${key}`, { method: "PATCH", body: JSON.stringify(change) });
