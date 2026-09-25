import { isShipped } from "./stages";

const DASHBOARD_STAGE = 5;

export const JOB_TITLES = ["clinician", "trial_coordinator", "secretary", "developer_admin"] as const;
export type JobTitle = (typeof JOB_TITLES)[number];

export const JOB_TITLE_LABEL: Record<JobTitle, string> = {
  clinician: "Clinician",
  trial_coordinator: "Trial coordinator",
  secretary: "Secretary",
  developer_admin: "Developer admin",
};

/** Developer admins configure and support Vigil but never see Patient data (design doc §6.4). */
export function seesPatientData(jobTitle: JobTitle): boolean {
  return jobTitle !== "developer_admin";
}

/** Change Settings (design doc §6.4). The backend enforces it; the UI just doesn't offer what would be refused. */
export function canChangeSettings(jobTitle: JobTitle): boolean {
  return jobTitle === "clinician" || jobTitle === "developer_admin";
}

/** Activate / deactivate Specialty Modules (design doc §6.4): developer admins only. */
export function canSwitchModules(jobTitle: JobTitle): boolean {
  return jobTitle === "developer_admin";
}

/** Home: the Dashboard for staff once it ships (Stage 5); until then, and always for developer admins, System status. */
export function homePath(jobTitle: JobTitle): string {
  return seesPatientData(jobTitle) && isShipped(DASHBOARD_STAGE) ? "/dashboard" : "/system";
}

export function isKnownJobTitle(value: unknown): value is JobTitle {
  return typeof value === "string" && (JOB_TITLES as readonly string[]).includes(value);
}
