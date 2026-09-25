"use client";

import { useId, useState, type ReactNode } from "react";
import { messageOf } from "@/lib/api";
import { JOB_TITLES, JOB_TITLE_LABEL, type JobTitle } from "@/lib/jobTitles";
import type { UserChange, UserRow } from "@/lib/users";

function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const titleId = useId();
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4" onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <div role="dialog" aria-modal="true" aria-labelledby={titleId} className="flex w-full max-w-[420px] flex-col gap-3 rounded-md border border-border bg-card p-5 shadow-card">
        <h2 id={titleId} className="m-0 text-base font-semibold">{title}</h2>
        {children}
      </div>
    </div>
  );
}

const field = "h-8 w-full rounded-md border border-border bg-background px-2 text-[13px]";

/** Both changes are recorded as a Verification in the acting User's name (design doc §6.4). */
function SignOffNote({ actor }: { actor: string }) {
  return <p className="m-0 text-xs text-muted-foreground">Recorded in the audit trail as a sign-off by {actor}.</p>;
}

function useSubmit(onSubmit: (change: UserChange) => Promise<void>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(change: UserChange) {
    setBusy(true);
    setError(null);
    try { await onSubmit(change); } catch (reason) { setError(messageOf(reason)); setBusy(false); }
  }
  return { busy, error, submit };
}

export function ChangeJobTitleDialog({ user, actor, onSubmit, onClose }: {
  user: UserRow; actor: string; onSubmit: (change: UserChange) => Promise<void>; onClose: () => void;
}) {
  const [jobTitle, setJobTitle] = useState<JobTitle>(user.job_title);
  const [reason, setReason] = useState("");
  const { busy, error, submit } = useSubmit(onSubmit);
  return (
    <Dialog title={`Change ${user.display_name}'s Job Title`} onClose={onClose}>
      <label className="flex flex-col gap-1 text-xs font-medium">
        Job Title
        <select value={jobTitle} onChange={(e) => setJobTitle(e.target.value as JobTitle)} className={field}>
          {JOB_TITLES.map((title) => <option key={title} value={title}>{JOB_TITLE_LABEL[title]}</option>)}
        </select>
      </label>
      {jobTitle === "developer_admin" && user.job_title !== "developer_admin" && (
        <p className="m-0 rounded-md border border-cau-bd bg-cau-bg p-2 text-xs text-cau">A developer admin can manage Users and Settings but will no longer see any Patient data or verify anything.</p>
      )}
      <label className="flex flex-col gap-1 text-xs font-medium">
        Reason (optional)
        <input value={reason} onChange={(e) => setReason(e.target.value)} className={field} />
      </label>
      <SignOffNote actor={actor} />
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button onClick={onClose} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        <button
          onClick={() => submit({ job_title: jobTitle, reason: reason.trim() || undefined })}
          disabled={busy || jobTitle === user.job_title}
          className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50"
        >
          Change Job Title
        </button>
      </div>
    </Dialog>
  );
}

export function SetActiveDialog({ user, actor, onSubmit, onClose }: {
  user: UserRow; actor: string; onSubmit: (change: UserChange) => Promise<void>; onClose: () => void;
}) {
  const deactivating = user.is_active;
  const [reason, setReason] = useState("");
  const { busy, error, submit } = useSubmit(onSubmit);
  return (
    <Dialog title={`${deactivating ? "Deactivate" : "Reactivate"} ${user.display_name}`} onClose={onClose}>
      <p className="m-0 text-[13px] text-muted-foreground">
        {deactivating
          ? "They won't be able to sign in. Nothing is deleted: everything they signed off stays in the audit trail."
          : "They'll be able to sign in again with their current Job Title."}
      </p>
      <label className="flex flex-col gap-1 text-xs font-medium">
        {deactivating ? "Reason (required)" : "Reason (optional)"}
        <input value={reason} onChange={(e) => setReason(e.target.value)} className={field} />
      </label>
      <SignOffNote actor={actor} />
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button onClick={onClose} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        <button
          onClick={() => submit({ is_active: !deactivating, reason: reason.trim() || undefined })}
          disabled={busy || (deactivating && !reason.trim())}
          className={`h-8 rounded-md px-3 text-[13px] font-medium disabled:opacity-50 ${deactivating ? "bg-neg text-white" : "bg-primary text-primary-foreground"}`}
        >
          {deactivating ? "Deactivate" : "Reactivate"}
        </button>
      </div>
    </Dialog>
  );
}
