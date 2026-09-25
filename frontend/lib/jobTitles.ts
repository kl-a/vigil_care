export const JOB_TITLES = ["clinician", "trial_coordinator", "secretary", "developer_admin"] as const;
export type JobTitle = (typeof JOB_TITLES)[number];

export const JOB_TITLE_LABEL: Record<JobTitle, string> = {
  clinician: "Clinician",
  trial_coordinator: "Trial coordinator",
  secretary: "Secretary",
  developer_admin: "Developer admin",
};

/** Developer admins never see Patient data, so their home is System status. */
export function homePath(jobTitle: JobTitle): string {
  return jobTitle === "developer_admin" ? "/system" : "/dashboard";
}

export function isJobTitle(value: unknown): value is JobTitle {
  return typeof value === "string" && (JOB_TITLES as readonly string[]).includes(value);
}
