import { request, type Schemas } from "@/lib/api";
import type { ModuleConfiguration } from "./types";

export type ModuleStatus = Schemas["ModuleStatus"];

/** The Practice's active modules, sections and Patient tabs (per-Practice activation, #15). */
export const fetchModuleConfiguration = () => request<ModuleConfiguration>("/modules/active");

export const listModules = () => request<ModuleStatus[]>("/modules");
export const setModuleActive = (key: string, change: { is_active: boolean; reason?: string }) =>
  request<ModuleStatus>(`/modules/${key}`, { method: "PATCH", body: JSON.stringify(change) });
