import { request, type Schemas } from "./api";

export type ProviderRow = Schemas["ProviderRow"];
export type NewProvider = Schemas["NewProvider"];
export type ProviderChange = Schemas["ProviderChange"];
export type ProviderSpecialty = ProviderRow["specialty"];

export const SPECIALTY_LABEL: Record<ProviderSpecialty, string> = {
  medical_oncology: "Medical oncology",
  radiation_oncology: "Radiation oncology",
  surgery: "Surgery",
  general_practice: "General practice",
  haematology: "Haematology",
  pathology: "Pathology",
  radiology: "Radiology",
  other: "Other",
};
export const SPECIALTIES = Object.keys(SPECIALTY_LABEL) as ProviderSpecialty[];

export interface ProviderFilters {
  q?: string;
  specialty?: ProviderSpecialty;
  internal?: boolean;
}

export function listProviders(filters: ProviderFilters = {}): Promise<ProviderRow[]> {
  const params = new URLSearchParams();
  if (filters.q?.trim()) params.set("q", filters.q.trim());
  if (filters.specialty) params.set("specialty", filters.specialty);
  if (filters.internal !== undefined) params.set("internal", String(filters.internal));
  const query = params.toString();
  return request<ProviderRow[]>(`/providers${query ? `?${query}` : ""}`);
}

export const fetchProvider = (id: string) => request<ProviderRow>(`/providers/${id}`);
export const addProvider = (provider: NewProvider) =>
  request<ProviderRow>("/providers", { method: "POST", body: JSON.stringify(provider) });
export const changeProvider = (id: string, change: ProviderChange) =>
  request<ProviderRow>(`/providers/${id}`, { method: "PATCH", body: JSON.stringify(change) });
export const deleteProvider = (id: string, reason: string) =>
  request<void>(`/providers/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });
