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

// --- Labs (#42) ---------------------------------------------------------------------------------------------

export type LabResultRow = Schemas["LabResultRow"];
export type LabFlag = NonNullable<LabResultRow["flag"]>;
export type NewLabPanel = Schemas["NewLabPanel"];
export type NewLabResult = Schemas["NewLabResult"];
export type LabResultChange = Schemas["LabResultChange"];

export const fetchLabResults = (patientId: string) => request<LabResultRow[]>(`/patients/${patientId}/labs`);
/** A panel of results in one save, with one Verification. */
export const addLabPanel = (patientId: string, panel: NewLabPanel) =>
  request<Schemas["LabPanelRow"]>(`/patients/${patientId}/lab-panels`, { method: "POST", body: JSON.stringify(panel) });
export const changeLabResult = (patientId: string, resultId: string, change: LabResultChange) =>
  request<LabResultRow>(`/patients/${patientId}/labs/${resultId}`, { method: "PATCH", body: JSON.stringify(change) });
export const removeLabResult = (patientId: string, resultId: string, reason: string) =>
  request<void>(`/patients/${patientId}/labs/${resultId}`, { method: "DELETE", body: JSON.stringify({ reason }) });

/** Common analytes, prefilled by panel with their usual Australian units; the reference range comes from the report. */
export const COMMON_PANELS: Record<string, { analyte: string; unit: string }[]> = {
  FBC: [
    { analyte: "Haemoglobin", unit: "g/L" }, { analyte: "White cell count", unit: "x10^9/L" },
    { analyte: "Neutrophils", unit: "x10^9/L" }, { analyte: "Lymphocytes", unit: "x10^9/L" }, { analyte: "Platelets", unit: "x10^9/L" },
  ],
  EUC: [
    { analyte: "Sodium", unit: "mmol/L" }, { analyte: "Potassium", unit: "mmol/L" }, { analyte: "Urea", unit: "mmol/L" },
    { analyte: "Creatinine", unit: "umol/L" }, { analyte: "eGFR", unit: "mL/min/1.73m2" },
  ],
  LFT: [
    { analyte: "Bilirubin", unit: "umol/L" }, { analyte: "ALT", unit: "U/L" }, { analyte: "AST", unit: "U/L" },
    { analyte: "ALP", unit: "U/L" }, { analyte: "GGT", unit: "U/L" }, { analyte: "Albumin", unit: "g/L" },
  ],
};

/** Each analyte's results, oldest first: a trend. Only numbers can be charted. */
export function trendsOf(results: LabResultRow[]): Map<string, LabResultRow[]> {
  const trends = new Map<string, LabResultRow[]>();
  for (const result of [...results].sort((a, b) => a.collected_at.localeCompare(b.collected_at))) {
    trends.set(result.analyte, [...(trends.get(result.analyte) ?? []), result]);
  }
  return trends;
}

// --- Plan and notes (#45) -----------------------------------------------------------------------------------

export type ManagementPlanRow = Schemas["ManagementPlanRow"];
export type ClinicalNoteRow = Schemas["ClinicalNoteRow"];
export type NoteType = ClinicalNoteRow["note_type"];
export type NextStepRow = Schemas["NextStepRow"];
export type NextStepKind = NextStepRow["kind"];

export const NOTE_TYPE_LABEL: Record<NoteType, string> = {
  clinical_note: "Clinical note", letter_to_referrer: "Letter to referrer", discharge_summary: "Discharge summary",
};
export const NEXT_STEP_KIND_LABEL: Record<NextStepKind, string> = {
  rescan: "Re-scan", mdt: "MDT", trial_window: "Trial window", review: "Review", other: "Other",
};

export const fetchManagementPlans = (patientId: string) => request<ManagementPlanRow[]>(`/patients/${patientId}/management-plans`);
export const addManagementPlan = (patientId: string, plan: Schemas["NewManagementPlan"]) =>
  request<ManagementPlanRow>(`/patients/${patientId}/management-plans`, { method: "POST", body: JSON.stringify(plan) });
export const changeManagementPlan = (patientId: string, planId: string, change: Schemas["ManagementPlanChange"]) =>
  request<ManagementPlanRow>(`/patients/${patientId}/management-plans/${planId}`, { method: "PATCH", body: JSON.stringify(change) });

export const fetchClinicalNotes = (patientId: string) => request<ClinicalNoteRow[]>(`/patients/${patientId}/clinical-notes`);
export const addClinicalNote = (patientId: string, note: Schemas["NewClinicalNote"]) =>
  request<ClinicalNoteRow>(`/patients/${patientId}/clinical-notes`, { method: "POST", body: JSON.stringify(note) });
export const removeClinicalNote = (patientId: string, noteId: string, reason: string) =>
  request<void>(`/patients/${patientId}/clinical-notes/${noteId}`, { method: "DELETE", body: JSON.stringify({ reason }) });

export const fetchNextSteps = (patientId: string) => request<NextStepRow[]>(`/patients/${patientId}/next-steps`);
export const addNextStep = (patientId: string, step: Schemas["NewNextStep"]) =>
  request<NextStepRow>(`/patients/${patientId}/next-steps`, { method: "POST", body: JSON.stringify(step) });
export const markNextStepDone = (patientId: string, stepId: string) =>
  request<NextStepRow>(`/patients/${patientId}/next-steps/${stepId}/done`, { method: "POST" });
export const removeNextStep = (patientId: string, stepId: string, reason: string) =>
  request<void>(`/patients/${patientId}/next-steps/${stepId}`, { method: "DELETE", body: JSON.stringify({ reason }) });

// --- Treatment Courses (#40) --------------------------------------------------------------------------------

export type TreatmentCourseRow = Schemas["TreatmentCourseRow"];
export type NewTreatmentCourse = Schemas["NewTreatmentCourse"];
export type Modality = TreatmentCourseRow["modality"];
export type Intent = NonNullable<TreatmentCourseRow["intent"]>;

export const MODALITY_LABEL: Record<Modality, string> = { systemic: "Systemic", surgery: "Surgery", radiation: "Radiation" };
export const INTENT_LABEL: Record<Intent, string> = { curative: "Curative", neoadjuvant: "Neoadjuvant", adjuvant: "Adjuvant", palliative: "Palliative" };

export const fetchTreatmentCourses = (patientId: string) => request<TreatmentCourseRow[]>(`/patients/${patientId}/treatment-courses`);
export const addTreatmentCourse = (patientId: string, course: NewTreatmentCourse) =>
  request<TreatmentCourseRow>(`/patients/${patientId}/treatment-courses`, { method: "POST", body: JSON.stringify(course) });
export const changeTreatmentCourse = (patientId: string, id: string, change: Schemas["TreatmentCourseChange"]) =>
  request<TreatmentCourseRow>(`/patients/${patientId}/treatment-courses/${id}`, { method: "PATCH", body: JSON.stringify(change) });
export const removeTreatmentCourse = (patientId: string, id: string, reason: string) =>
  request<void>(`/patients/${patientId}/treatment-courses/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });
