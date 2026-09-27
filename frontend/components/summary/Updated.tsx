"use client";

import Link from "next/link";
import { JOB_TITLE_LABEL, isKnownJobTitle } from "@/lib/jobTitles";
import { formatWhen } from "@/lib/users";

const ACTION: Record<string, string> = {
  edit: "Entered or corrected", attribute: "Attributed", override: "Overridden", move: "Moved", delete: "Removed", reject: "Ruled out",
};

/** Who last changed a section, and when: the Verification of its newest value, and where to see it in full. */
export function Updated({ updated, href }: { updated: { by: string; job_title: string; at: string; action?: string } | null | undefined; href?: string }) {
  if (!updated) return null;
  const jobTitle = isKnownJobTitle(updated.job_title) ? JOB_TITLE_LABEL[updated.job_title] : updated.job_title;
  return (
    <details className="text-xs text-muted-foreground">
      <summary className="cursor-pointer">Last updated {formatWhen(updated.at)}</summary>
      <span className="flex flex-wrap gap-x-2">
        <span>{ACTION[updated.action ?? "edit"] ?? "Changed"} by {updated.by} ({jobTitle})</span>
        {href && <Link href={href} className="text-primary" data-noprint>See it in the record</Link>}
      </span>
    </details>
  );
}
