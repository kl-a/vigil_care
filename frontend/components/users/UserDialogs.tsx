"use client";

import { useState } from "react";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { SignOffDialog } from "@/components/dialogs/SignOffDialog";
import { FIELD } from "@/components/ui/styles";
import { JOB_TITLES, JOB_TITLE_LABEL, type JobTitle } from "@/lib/jobTitles";
import type { UserChange, UserRow } from "@/lib/users";

interface Props { user: UserRow; actor: string; onSubmit: (change: UserChange) => Promise<void>; onClose: () => void }

/** Screen 18: Change Job Title is a SignOffDialog (docs/frontend-design.md §8). */
export function ChangeJobTitleDialog({ user, actor, onSubmit, onClose }: Props) {
  const [jobTitle, setJobTitle] = useState<JobTitle>(user.job_title);
  const [reason, setReason] = useState("");
  return (
    <SignOffDialog
      title={`Change ${user.display_name}'s Job Title`}
      actor={actor}
      confirmLabel="Change Job Title"
      canConfirm={jobTitle !== user.job_title}
      onConfirm={() => onSubmit({ job_title: jobTitle, reason: reason.trim() || undefined })}
      onClose={onClose}
    >
      <label className="flex flex-col gap-1 text-xs font-medium">
        Job Title
        <select id="change-job-title" value={jobTitle} onChange={(e) => setJobTitle(e.target.value as JobTitle)} className={FIELD}>
          {JOB_TITLES.map((title) => <option key={title} value={title}>{JOB_TITLE_LABEL[title]}</option>)}
        </select>
      </label>
      {jobTitle === "developer_admin" && user.job_title !== "developer_admin" && (
        <p className="m-0 rounded-md border border-cau-bd bg-cau-bg p-2 text-xs text-cau">A developer admin can manage Users and Settings but will no longer see any Patient data or verify anything.</p>
      )}
      <label className="flex flex-col gap-1 text-xs font-medium">
        Reason (optional)
        <input id="change-job-title-reason" value={reason} onChange={(e) => setReason(e.target.value)} className={FIELD} />
      </label>
    </SignOffDialog>
  );
}

/** Screen 18: Deactivate is a ReasonDialog; reactivating takes an optional reason. */
export function SetActiveDialog({ user, actor, onSubmit, onClose }: Props) {
  const deactivating = user.is_active;
  return (
    <ReasonDialog
      title={`${deactivating ? "Deactivate" : "Reactivate"} ${user.display_name}`}
      actor={actor}
      confirmLabel={deactivating ? "Deactivate" : "Reactivate"}
      reasonRequired={deactivating}
      danger={deactivating}
      onConfirm={(reason) => onSubmit({ is_active: !deactivating, reason })}
      onClose={onClose}
    >
      <p className="m-0 text-[13px] text-muted-foreground">
        {deactivating
          ? "They won't be able to sign in. Nothing is deleted: everything they signed off stays in the audit trail."
          : "They'll be able to sign in again with their current Job Title."}
      </p>
    </ReasonDialog>
  );
}
