"use client";

import Link from "next/link";
import { VerifiedMark } from "@/components/ui/Verified";
import { formatDate } from "@/lib/format";
import { JOB_TITLE_LABEL, isKnownJobTitle, type JobTitle } from "@/lib/jobTitles";

type Updated = { by: string; job_title: string; at: string; subject_table?: string; subject_id?: string };

/**
 * A section's meta line: when it was last updated, a ✓ that says who verified its newest value (hover) and
 * shows that value's history (click), and where to see it in the record.
 */
export function Updated({ updated, href }: { updated: Updated | null | undefined; href?: string }) {
  if (!updated) return null;
  const jobTitle = isKnownJobTitle(updated.job_title) ? JOB_TITLE_LABEL[updated.job_title] : updated.job_title;
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span>Updated {formatDate(updated.at)}</span>
      {updated.subject_table && updated.subject_id && isKnownJobTitle(updated.job_title)
        ? <VerifiedMark subjectTable={updated.subject_table} subjectId={updated.subject_id}
            entered={{ by: updated.by, job_title: updated.job_title as JobTitle, at: updated.at }} />
        : <span>by {updated.by} ({jobTitle})</span>}
      {href && <>· <Link href={href} className="text-primary" data-noprint>See it in the record</Link></>}
    </span>
  );
}
