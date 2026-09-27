import { request, type Schemas } from "./api";

export type MedicationRow = Schemas["MedicationRow"];
export type NewMedication = Schemas["NewMedication"];
export type MedicationChange = Schemas["MedicationChange"];
export type MedicationChangeRow = Schemas["MedicationChangeRow"];
export type DrugOption = Schemas["DrugOption"];
export type Frequency = NonNullable<MedicationRow["frequency"]>;
export type Route = NonNullable<MedicationRow["route"]>;
export type Category = NonNullable<MedicationRow["category"]>;
export type MedicationStatus = MedicationRow["status"];
export type ChangeType = MedicationChangeRow["change_type"];

export const FREQUENCY_LABEL: Record<Frequency, string> = {
  daily: "Once daily", twice_daily: "Twice daily", three_times_daily: "Three times daily", weekly: "Weekly", fortnightly: "Fortnightly",
  monthly: "Monthly", prn: "When needed (PRN)", stat: "Once only (stat)", other: "Other",
};
export const ROUTE_LABEL: Record<Route, string> = {
  oral: "Oral", iv: "IV", subcut: "Subcutaneous", im: "IM", topical: "Topical", inhaled: "Inhaled", pr: "PR", other: "Other",
};
export const CATEGORY_LABEL: Record<Category, string> = {
  cancer_treatment: "Cancer treatment", supportive_care: "Supportive care", comorbidity_management: "Other condition",
  supplement: "Supplement", other: "Other",
};
export const STATUS_LABEL: Record<MedicationStatus, string> = {
  active: "Active", on_hold: "On hold", unknown: "Status unknown", discontinued: "Discontinued", completed: "Completed",
};
export const CHANGE_LABEL: Record<ChangeType, string> = {
  added: "Added", dose_changed: "Dose changed", discontinued: "Stopped", restarted: "Restarted", status_changed: "Status changed",
  verified: "Verified", corrected: "Corrected",
};

/** Active and discontinued, as the Medication Manager's tabs split them. */
export const isStopped = (medication: Pick<MedicationRow, "status">) => medication.status === "discontinued" || medication.status === "completed";

export const searchDrugs = (q: string) => request<DrugOption[]>(`/drugs?${new URLSearchParams({ q })}`);
export const fetchMedications = (patientId: string) => request<MedicationRow[]>(`/patients/${patientId}/medications`);
export const fetchMedicationChanges = (patientId: string) => request<MedicationChangeRow[]>(`/patients/${patientId}/medication-changes`);
export const addMedication = (patientId: string, medication: NewMedication) =>
  request<MedicationRow>(`/patients/${patientId}/medications`, { method: "POST", body: JSON.stringify(medication) });
/** A change always says why, once for the whole save. */
export const changeMedication = (patientId: string, id: string, change: MedicationChange) =>
  request<MedicationRow>(`/patients/${patientId}/medications/${id}`, { method: "PATCH", body: JSON.stringify(change) });
export const stopMedication = (patientId: string, id: string, endDate: string, reason: string) =>
  request<MedicationRow>(`/patients/${patientId}/medications/${id}/stop`, { method: "POST", body: JSON.stringify({ end_date: endDate, reason }) });
export const restartMedication = (patientId: string, id: string, reason: string) =>
  request<MedicationRow>(`/patients/${patientId}/medications/${id}/restart`, { method: "POST", body: JSON.stringify({ reason }) });
export const removeMedication = (patientId: string, id: string, reason: string) =>
  request<void>(`/patients/${patientId}/medications/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });

/** How it's taken, e.g. "5 mg · Oral · Twice daily". */
export function howTaken(m: Pick<MedicationRow, "dose_display" | "route" | "frequency" | "frequency_detail">): string {
  const frequency = m.frequency && (m.frequency === "other" && m.frequency_detail ? m.frequency_detail : FREQUENCY_LABEL[m.frequency]);
  return [m.dose_display, m.route && ROUTE_LABEL[m.route], frequency].filter(Boolean).join(" · ") || "Dose not recorded";
}
