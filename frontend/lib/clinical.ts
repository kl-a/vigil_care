import { request, type Schemas } from "./api";

export type ConditionRow = Schemas["ConditionRow"];
export type NewCondition = Schemas["NewCondition"];
export type ConditionChange = Schemas["ConditionChange"];
export type ConditionStatus = ConditionRow["status"];
export type Entered = Schemas["Entered"];
export type ModuleFacts = Schemas["ModuleFacts"];

export const CONDITION_STATUS_LABEL: Record<ConditionStatus, string> = { active: "Active", resolved: "Resolved" };

/** Which Clinical Record kinds the signed-in User may enter by hand (Verification Rights, design doc §6.4). */
export const fetchEntryRights = () => request<Record<string, boolean>>("/clinical/entry-rights");

export const fetchConditions = (patientId: string) => request<ConditionRow[]>(`/patients/${patientId}/conditions`);
export const addCondition = (patientId: string, condition: NewCondition) =>
  request<ConditionRow>(`/patients/${patientId}/conditions`, { method: "POST", body: JSON.stringify(condition) });
/** A correction always says why, once for the whole save. */
export const changeCondition = (patientId: string, conditionId: string, change: ConditionChange) =>
  request<ConditionRow>(`/patients/${patientId}/conditions/${conditionId}`, { method: "PATCH", body: JSON.stringify(change) });
export const removeCondition = (patientId: string, conditionId: string, reason: string) =>
  request<void>(`/patients/${patientId}/conditions/${conditionId}`, { method: "DELETE", body: JSON.stringify({ reason }) });

/** Facts recorded by Specialty Modules inactive at this Practice, in plain words (ADR 0004, amended). */
export const fetchInactiveModuleFacts = (patientId: string) => request<ModuleFacts[]>(`/patients/${patientId}/inactive-module-facts`);

/** The fields of `next` that differ from `current`: a save sends only what changed. */
export function changesBetween<T extends Record<string, unknown>>(current: T, next: T): Partial<T> {
  return Object.fromEntries(Object.entries(next).filter(([key, value]) => (current[key] ?? null) !== (value ?? null))) as Partial<T>;
}
