import { request, type Schemas } from "./api";

export type PatientRow = Schemas["PatientRow"];
export type PatientDetail = Schemas["PatientDetail"];
export type PatientIdentity = Schemas["IdentityDetails"];
export type NewPatient = Schemas["NewPatient"];
export type IdentityChange = Schemas["IdentityChange"];
export type IdentityHistoryEntry = Schemas["IdentityHistoryEntry"];

export type IdentityField = keyof PatientIdentity;

/** Patient Identity fields in form order (design doc §5 screen 3: name, DOB, Medicare + IRN, IHI, MRN, contact, next of kin). */
export const IDENTITY_FIELDS: { key: IdentityField; label: string; required?: boolean; type?: "date"; mono?: boolean; hint?: string }[] = [
  { key: "given_name", label: "Given name", required: true },
  { key: "family_name", label: "Family name", required: true },
  { key: "dob", label: "Date of birth", type: "date" },
  { key: "mrn", label: "MRN", mono: true },
  { key: "medicare_number", label: "Medicare number", mono: true, hint: "10 digits" },
  { key: "medicare_irn", label: "IRN", mono: true, hint: "1–9" },
  { key: "ihi", label: "IHI", mono: true, hint: "16 digits" },
  { key: "address", label: "Address" },
  { key: "phone", label: "Phone" },
  { key: "mobile", label: "Mobile" },
  { key: "email", label: "Email" },
  { key: "next_of_kin_name", label: "Next of kin" },
  { key: "next_of_kin_phone", label: "Next of kin phone" },
];

export const IDENTITY_LABEL = Object.fromEntries(IDENTITY_FIELDS.map((f) => [f.key, f.label])) as Record<IdentityField, string>;

export const listPatients = (q?: string) =>
  request<PatientRow[]>(`/patients${q?.trim() ? `?q=${encodeURIComponent(q.trim())}` : ""}`);
export const fetchPatient = (id: string) => request<PatientDetail>(`/patients/${id}`);
export const createPatient = (patient: NewPatient) =>
  request<PatientDetail>("/patients", { method: "POST", body: JSON.stringify(patient) });
export const changeIdentity = (id: string, change: IdentityChange) =>
  request<PatientDetail>(`/patients/${id}/identity`, { method: "PATCH", body: JSON.stringify(change) });

/** Soft delete (#17): hidden from lists and search, never erased. */
export const removePatient = (id: string, reason: string) =>
  request<void>(`/patients/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });

/** "03/04/1962 (64)": Australian date order, with age in whole years. */
export function formatDob(dob: string | null | undefined, today: Date = new Date()): string {
  if (!dob) return "—";
  const [year, month, day] = dob.split("-").map(Number) as [number, number, number];
  let age = today.getFullYear() - year;
  if (today.getMonth() + 1 < month || (today.getMonth() + 1 === month && today.getDate() < day)) age -= 1;
  return `${String(day).padStart(2, "0")}/${String(month).padStart(2, "0")}/${year} (${age})`;
}
