"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { JobTitleChip } from "@/components/users/JobTitleChip";
import { ChangeJobTitleDialog, SetActiveDialog } from "@/components/users/UserDialogs";
import { messageOf } from "@/lib/api";
import { JOB_TITLES, JOB_TITLE_LABEL, type JobTitle } from "@/lib/jobTitles";
import { changeUser, createUser, formatWhen, listUsers, type UserChange, type UserRow } from "@/lib/users";

type Dialog = { kind: "job_title" | "active"; user: UserRow } | null;

const field = "h-8 rounded-md border border-border bg-background px-2 text-[13px]";

/** User Management (design doc §5 screen 18). Clinicians, secretaries and developer admins (§6.4). */
export default function UserManagementPage() {
  const me = useSignedInUser();
  const [users, setUsers] = useState<UserRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [dialog, setDialog] = useState<Dialog>(null);

  const load = useCallback(() => {
    listUsers().then(setUsers).catch((reason: unknown) => setError(messageOf(reason)));
  }, []);
  useEffect(load, [load]);

  async function apply(user: UserRow, change: UserChange) {
    await changeUser(user.id, change);
    setDialog(null);
    load();
  }

  const actor = `${me.display_name} (${JOB_TITLE_LABEL[me.job_title]})`;
  return (
    <div data-screen-label="User Management" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="m-0 text-xl font-semibold">User Management</h1>
        <button onClick={() => setAdding(true)} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">New User</button>
      </div>
      <p className="m-0 max-w-[70ch] text-[13px] text-muted-foreground">
        Who can use Vigil at {me.practice_name}, and their Job Title. Every change is signed off in your name. Users are deactivated, never deleted.
      </p>
      {adding && <NewUserForm onDone={() => { setAdding(false); load(); }} onCancel={() => setAdding(false)} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {users === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Users…</p>}
      {users && (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="w-full border-collapse text-[13px]">
            <thead className="bg-muted text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">Job Title</th>
                <th className="px-3 py-2 font-medium">Provider record</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Last login</th>
                <th className="px-3 py-2 font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-t border-border">
                  <td className="px-3 py-2">
                    <Link href={`/users/${user.id}`} className="font-medium text-foreground">{user.display_name}</Link>
                    <div className="font-mono text-[11px] text-muted-foreground">{user.username}</div>
                  </td>
                  <td className="px-3 py-2"><JobTitleChip jobTitle={user.job_title} /></td>
                  <td className="px-3 py-2 text-muted-foreground">{user.provider_id ? "Linked" : "—"}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full border px-2 py-0.5 text-xs ${user.is_active ? "border-pos-bd bg-pos-bg text-pos" : "border-neu-bd bg-neu-bg text-neu"}`}>
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{formatWhen(user.last_login_at)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    {user.id === me.id ? (
                      <span className="text-xs text-muted-foreground">You</span>
                    ) : (
                      <span className="inline-flex gap-2">
                        <button onClick={() => setDialog({ kind: "job_title", user })} className="text-xs font-medium text-primary">Change Job Title</button>
                        <button onClick={() => setDialog({ kind: "active", user })} className={`text-xs font-medium ${user.is_active ? "text-neg" : "text-primary"}`}>
                          {user.is_active ? "Deactivate" : "Reactivate"}
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {dialog?.kind === "job_title" && (
        <ChangeJobTitleDialog user={dialog.user} actor={actor} onSubmit={(change) => apply(dialog.user, change)} onClose={() => setDialog(null)} />
      )}
      {dialog?.kind === "active" && (
        <SetActiveDialog user={dialog.user} actor={actor} onSubmit={(change) => apply(dialog.user, change)} onClose={() => setDialog(null)} />
      )}
    </div>
  );
}

function NewUserForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [jobTitle, setJobTitle] = useState<JobTitle>("secretary");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createUser({ display_name: displayName.trim(), username: username.trim(), job_title: jobTitle });
      onDone();
    } catch (reason) {
      setError(messageOf(reason));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="New User" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <h2 className="m-0 text-sm font-semibold">New User</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Name
          <input id="new-user-name" required value={displayName} onChange={(e) => setDisplayName(e.target.value)} className={field} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Username
          <input id="new-user-username" required value={username} onChange={(e) => setUsername(e.target.value.toLowerCase())}
            placeholder="e.g. riley.hart" pattern="[a-z0-9][a-z0-9._\-]{2,39}" title="3–40 lowercase letters, digits, dots, dashes or underscores" className={`${field} font-mono`} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Job Title
          <select id="new-user-job-title" value={jobTitle} onChange={(e) => setJobTitle(e.target.value as JobTitle)} className={field}>
            {JOB_TITLES.map((title) => <option key={title} value={title}>{JOB_TITLE_LABEL[title]}</option>)}
          </select>
        </label>
      </div>
      <p className="m-0 text-xs text-muted-foreground">They sign in with the dev login for now; password and 2FA enrolment arrive in Stage 13.</p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        <button type="submit" disabled={busy} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">Add User</button>
      </div>
    </form>
  );
}
