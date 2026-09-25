import { JOB_TITLE_LABEL, type JobTitle } from "@/lib/jobTitles";

export function JobTitleChip({ jobTitle }: { jobTitle: JobTitle }) {
  const tone = jobTitle === "developer_admin" ? "border-dev/40 bg-dev-bg text-dev" : "border-border bg-muted text-foreground";
  return <span className={`rounded-full border px-2 py-0.5 text-xs ${tone}`}>{JOB_TITLE_LABEL[jobTitle]}</span>;
}
