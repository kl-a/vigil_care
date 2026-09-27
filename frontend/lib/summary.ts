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

const DAY = 24 * 60 * 60 * 1000;

/** How long an Open Item has been waiting, or when a Next Step is due: "3 d", "due 3 d", "2 d overdue", "today". */
export function ageOf(item: Pick<OpenItem, "type" | "dated">, today: Date = new Date()): string {
  if (!item.dated) return "—";
  const [y, m, d] = item.dated.split("-").map(Number) as [number, number, number];
  const days = Math.round((Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) - Date.UTC(y, m - 1, d)) / DAY);
  const span = (n: number) => (n >= 60 ? `${Math.round(n / 30)} mo` : `${n} d`);
  if (item.type === "next_step") return days === 0 ? "due today" : days < 0 ? `due ${span(-days)}` : `${span(days)} overdue`;
  return days <= 0 ? "today" : span(days);
}
