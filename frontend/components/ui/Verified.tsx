"use client";

import { CircleCheck } from "lucide-react";
import { useState } from "react";
import { Dialog } from "@/components/dialogs/Dialog";
import { request, type Schemas } from "@/lib/api";
import { formatWhen } from "@/lib/format";
import { JOB_TITLE_LABEL, isKnownJobTitle } from "@/lib/jobTitles";

type HistoryEntry = Schemas["ValueHistoryEntry"];
type Entered = Schemas["Entered"];

export const fetchValueHistory = (subjectTable: string, subjectId: string) =>
  request<HistoryEntry[]>(`/verifications/${subjectTable}/${subjectId}`);

const jobTitle = (title: string) => (isKnownJobTitle(title) ? JOB_TITLE_LABEL[title] : title);

/** What a Verification did, as the hover says it: "Verified by …" for entry, "Corrected by …: why" after. */
export function describe(entry: Pick<HistoryEntry, "action" | "by" | "job_title" | "at" | "reason" | "before">): string {
  const verb = entry.action === "edit" ? (entry.before ? "Corrected" : "Verified")
    : ({ attribute: "Attributed", override: "Overridden", move: "Moved", accept: "Seen", reject: "Ruled out", delete: "Removed" } as Record<string, string>)[entry.action] ?? "Changed";
  return `${verb} by ${entry.by} (${jobTitle(entry.job_title)}), ${formatWhen(entry.at)}${entry.reason ? `: ${entry.reason}` : ""}`;
}

/**
 * ✓ Verified (frontend-design §7), in place of "Entered by …" text: hover shows the value's latest Verification,
 * click opens its whole history. `entered` (who first entered it) shows until the history has loaded.
 */
export function VerifiedMark({ subjectTable, subjectId, entered }: { subjectTable: string; subjectId: string; entered?: Entered | null }) {
  const [history, setHistory] = useState<HistoryEntry[] | null>(null);
  const [showing, setShowing] = useState(false);
  const [open, setOpen] = useState(false);
  const load = () => { if (history === null) fetchValueHistory(subjectTable, subjectId).then(setHistory).catch(() => setHistory([])); };
  const latest = history?.[0];
  const summary = latest ? describe(latest)
    : entered ? `Verified by ${entered.by} (${jobTitle(entered.job_title)}), ${formatWhen(entered.at)}` : "Verified";
  return (
    <span className="relative inline-flex">
      <button type="button" aria-label={summary} onClick={() => { load(); setOpen(true); }}
        onMouseEnter={() => { load(); setShowing(true); }} onMouseLeave={() => setShowing(false)}
        onFocus={() => { load(); setShowing(true); }} onBlur={() => setShowing(false)}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full text-pos hover:bg-pos-bg">
        <CircleCheck aria-hidden className="h-4 w-4" />
      </button>
      {showing && !open && (
        <span role="tooltip" className="absolute bottom-6 left-1/2 z-30 w-max max-w-[320px] -translate-x-1/2 rounded-md border border-border bg-card px-2.5 py-1.5 text-xs text-foreground shadow-card">
          {summary}
        </span>
      )}
      {open && (
        <Dialog title="History of this value" onClose={() => setOpen(false)}>
          {history === null && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
          {history && history.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">No history recorded.</p>}
          {history && history.length > 0 && (
            <ol aria-label="History" className="m-0 flex list-none flex-col gap-2 p-0 text-[13px]">
              {history.map((h, i) => <li key={i} className="border-l-2 border-border pl-3">{describe(h)}</li>)}
            </ol>
          )}
          <div className="flex justify-end"><button onClick={() => setOpen(false)} className="h-8 rounded-md border border-border px-3 text-[13px]">Close</button></div>
        </Dialog>
      )}
    </span>
  );
}
