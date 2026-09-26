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

// Dates moved to lib/dates; re-exported for the Care Team screens that import them from here.
export { formatDate, todayIso } from "./dates";
