import { request, type Schemas } from "./api";

export type CareTeamRow = Schemas["CareTeamRow"];
export type NewCareTeamMember = Schemas["NewCareTeamMember"];
export type CareTeamChange = Schemas["CareTeamChange"];
export type ProviderPatientRow = Schemas["ProviderPatientRow"];
export type CareTeamRole = CareTeamRow["role"];

export const CARE_TEAM_ROLE_LABEL: Record<CareTeamRole, string> = {
  treating_oncologist: "Treating oncologist",
  referring_gp: "Referring GP",
  referring_specialist: "Referring specialist",
  surgeon: "Surgeon",
  radiation_oncologist: "Radiation oncologist",
  trial_site_contact: "Trial-site contact",
};
export const CARE_TEAM_ROLES = Object.keys(CARE_TEAM_ROLE_LABEL) as CareTeamRole[];

export const fetchCareTeam = (patientId: string) => request<CareTeamRow[]>(`/patients/${patientId}/care-team`);
export const addCareTeamMember = (patientId: string, member: NewCareTeamMember) =>
  request<CareTeamRow>(`/patients/${patientId}/care-team`, { method: "POST", body: JSON.stringify(member) });
export const changeCareTeamMember = (patientId: string, memberId: string, change: CareTeamChange) =>
  request<CareTeamRow>(`/patients/${patientId}/care-team/${memberId}`, { method: "PATCH", body: JSON.stringify(change) });
export const fetchProviderPatients = (providerId: string) => request<ProviderPatientRow[]>(`/providers/${providerId}/patients`);

/** "01/03/2024", or "—". */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}

/** Today in the browser's calendar, as the API's ISO date. */
export function todayIso(now: Date = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
