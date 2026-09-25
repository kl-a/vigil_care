import Link from "next/link";
import { ShieldOff } from "lucide-react";
import { JOB_TITLE_LABEL, homePath, type JobTitle } from "@/lib/jobTitles";

export function Forbidden({ jobTitle }: { jobTitle: JobTitle }) {
  const message = jobTitle === "developer_admin"
    ? "Developer admins never see Patient data. Patient screens are not available for this Job Title."
    : `This page isn't available to a ${JOB_TITLE_LABEL[jobTitle]}.`;
  return (
    <div className="flex flex-1 items-center justify-center p-10">
      <div className="flex max-w-[420px] flex-col items-center gap-2.5 text-center">
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-neu-bg text-neu"><ShieldOff aria-hidden className="h-5 w-5" /></span>
        <h1 className="m-0 text-lg font-semibold">Not available for your Job Title</h1>
        <p className="m-0 text-[13px] text-muted-foreground">{message}</p>
        <Link href={homePath(jobTitle)} className="text-[13px] font-medium text-primary">Go to your home page</Link>
      </div>
    </div>
  );
}
