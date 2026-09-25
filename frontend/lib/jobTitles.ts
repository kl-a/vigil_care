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

/**
 * UI mirrors of two §6.4 rows, so the screen doesn't offer what the backend would refuse. The backend
 * (core/permissions.py) is the authority; these only decide what to show.
 */

/** Change Settings. */
export function canChangeSettings(jobTitle: JobTitle): boolean {
  return jobTitle === "clinician" || jobTitle === "developer_admin";
}

/** Activate / deactivate Specialty Modules: developer admins only. */
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

/** How a signed-off change names the User: "Dr Alex Rivera (Clinician)". */
export function signOffName(user: { display_name: string; job_title: JobTitle }): string {
  return `${user.display_name} (${JOB_TITLE_LABEL[user.job_title]})`;
}
