import { request, type Schemas } from "./api";

export type OpenItem = Schemas["OpenItem"];
export type OpenItemAction = Schemas["OpenItemAction"];
export type Who = OpenItem["who"];
export type PatientSummary = Schemas["PatientSummary"];
export type LastUpdated = Schemas["LastUpdated"];

export const fetchPatientOpenItems = (patientId: string) => request<OpenItem[]>(`/patients/${patientId}/open-items`);
/** The Practice's queue (the Dashboard). */
export const fetchOpenItems = () => request<OpenItem[]>("/open-items");
export const fetchPatientSummary = (patientId: string) => request<PatientSummary>(`/patients/${patientId}/summary`);

/** Clears an Open Item by doing what's behind it, as the signed-in User. */
export function act(action: OpenItemAction, value?: string): Promise<unknown> {
  const body = action.input === "choose" && action.field ? { [action.field]: value }
    : action.input === "note" ? { note: value?.trim() || null }
    : action.input === "reason" ? { reason: value?.trim() ?? "" } : {};
  return request(action.path, { method: "POST", body: JSON.stringify(body) });
}

export const WHO_LABEL: Record<Who, string> = { staff: "Any staff", clinician: "Clinician only" };

/** Whether this Job Title may act on an Open Item. */
export const mayAct = (who: Who, jobTitle: string) => (who === "clinician" ? jobTitle === "clinician" : jobTitle !== "developer_admin");
