"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { messageOf } from "@/lib/api";
import { JOB_TITLE_LABEL, isKnownJobTitle } from "@/lib/jobTitles";
import { fetchUser, formatWhen, type HistoryEntry, type UserDetail } from "@/lib/users";
import { JobTitleChip } from "@/components/users/JobTitleChip";

function describe(entry: HistoryEntry): string {
  const before = entry.before ?? {};
  const after = entry.after ?? {};
  if (!entry.before && typeof after.job_title === "string") return `Added as ${label(after.job_title)}`;
  if ("job_title" in after) return `Job Title changed from ${label(before.job_title)} to ${label(after.job_title)}`;
  if ("is_active" in after) return after.is_active ? "Reactivated" : "Deactivated";
  return entry.action;
}

function label(value: unknown): string {
  return isKnownJobTitle(value) ? JOB_TITLE_LABEL[value] : String(value);
}

/** One User and their audit trail: every Job Title change and (de)activation, who signed it off and when. */
export default function UserPage({ params }: { params: { id: string } }) {
  const [user, setUser] = useState<UserDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUser(params.id).then(setUser).catch((reason: unknown) => setError(messageOf(reason)));
  }, [params.id]);

  return (
    <div data-screen-label="User" className="flex w-full max-w-[900px] flex-col gap-4 px-5 pb-8 pt-3">
      <Link href="/users" className="text-xs text-primary">← All Users</Link>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {!user && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {user && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="m-0 text-xl font-semibold">{user.display_name}</h1>
            <JobTitleChip jobTitle={user.job_title} />
            {!user.is_active && <span className="rounded-full border border-neu-bd bg-neu-bg px-2 py-0.5 text-xs text-neu">Inactive</span>}
          </div>
          <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-[13px]">
            <dt className="text-muted-foreground">Username</dt><dd className="m-0 font-mono">{user.username}</dd>
            <dt className="text-muted-foreground">Last login</dt><dd className="m-0">{formatWhen(user.last_login_at)}</dd>
            <dt className="text-muted-foreground">Provider record</dt><dd className="m-0">{user.provider_id ? "Linked" : "Not linked"}</dd>
          </dl>
          <section className="flex flex-col gap-2">
            <h2 className="m-0 text-sm font-semibold">Audit trail</h2>
            {user.history.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">No changes recorded.</p>}
            <ol className="m-0 flex list-none flex-col gap-2 p-0">
              {user.history.map((entry, index) => (
                <li key={index} className="rounded-md border border-border bg-card px-3 py-2 text-[13px]">
                  <div className="font-medium">{describe(entry)}</div>
                  <div className="text-xs text-muted-foreground">
                    Signed off by {entry.by_display_name} ({label(entry.by_job_title)}) · {formatWhen(entry.at)}
                  </div>
                  {entry.reason && <div className="mt-1 text-xs">Reason: {entry.reason}</div>}
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </div>
  );
}
