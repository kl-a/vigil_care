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

export function homePath(jobTitle: JobTitle): string {
  return seesPatientData(jobTitle) ? "/dashboard" : "/system";
}
