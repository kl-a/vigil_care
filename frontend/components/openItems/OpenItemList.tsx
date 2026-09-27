"use client";

import { CalendarClock, CircleAlert, CircleHelp, GitCompare, ScanSearch, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { act, mayAct, WHO_LABEL, type OpenItem, type OpenItemAction } from "@/lib/summary";

/** Each kind of Open Item's icon (the item names which; frontend-design §4.4: one fixed icon per meaning). */
const ICON: Record<OpenItem["icon"], LucideIcon> = { calendar: CalendarClock, compare: GitCompare, help: CircleHelp, scan: ScanSearch, alert: CircleAlert };

/**
 * Open Items (#48, design doc §6.3): each says what needs doing and clears only when someone does it: no dismiss,
 * no snooze. Actions come with the item (from the Core or a Specialty Module), so this list needs to know nothing
 * about them. Those a User's Job Title can't take show a "Needs clinician" lock.
 */
export function OpenItemList({ items, showPatient = false, onActed }: { items: OpenItem[]; showPatient?: boolean; onActed: () => void }) {
  if (items.length === 0) return <p className="m-0 text-[13px] text-muted-foreground">None: nothing needs acting on.</p>;
  return (
    <ul aria-label="Open Items" className="m-0 flex list-none flex-col divide-y divide-border p-0">
      {items.map((item) => <Item key={`${item.type}:${item.subject_id}`} item={item} showPatient={showPatient} onActed={onActed} />)}
    </ul>
  );
}

function Item({ item, showPatient, onActed }: { item: OpenItem; showPatient: boolean; onActed: () => void }) {
  const me = useSignedInUser();
  const canAct = mayAct(item.who, me.job_title);
  const Icon = ICON[item.icon];
  const [error, setError] = useState<string | null>(null);
  async function run(action: OpenItemAction, value?: string) {
    setError(null);
    try { await act(action, value); onActed(); } catch (reason) { setError(messageOf(reason)); }
  }
  return (
    <li className="flex flex-wrap items-start justify-between gap-3 py-2.5 text-[13px]">
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-2">
          <StatusPill tone="cau"><span className="inline-flex items-center gap-1"><Icon aria-hidden className="h-3 w-3" />{item.type_label}</span></StatusPill>
          {showPatient && <Link href={`/patients/${item.patient_id}/summary`} className="font-medium text-foreground underline-offset-2 hover:underline">{item.patient_name}</Link>}
          <span className="font-medium">{item.title}</span>
          <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">{WHO_LABEL[item.who]}</span>
        </span>
        <span className="text-xs text-muted-foreground">
          {item.detail}{item.dated && !item.detail?.includes(formatDate(item.dated)) && ` · ${formatDate(item.dated)}`}
        </span>
        {error && <span role="alert" className="text-xs text-neg">{error}</span>}
      </span>
      <span className="inline-flex flex-wrap items-center gap-2" data-noprint>
        {canAct ? item.actions.map((action) => <ActionControl key={action.label} action={action} onRun={(value) => run(action, value)} />) : <EntryLock who="clinician" />}
        <Link href={`/patients/${item.patient_id}/${item.open_tab}`} className="text-xs font-medium text-primary">Open</Link>
      </span>
    </li>
  );
}

function ActionControl({ action, onRun }: { action: OpenItemAction; onRun: (value?: string) => void }) {
  const [text, setText] = useState("");
  if (action.input === "choose") {
    if (!action.choices?.length) return <span className="text-xs text-muted-foreground">Nothing to {action.label.toLowerCase()} it to yet</span>;
    return (
      <select aria-label={`${action.label} to`} value="" onChange={(e) => e.target.value && onRun(e.target.value)} className={`${FIELD} h-7 w-48 text-xs`}>
        <option value="">{action.label} to…</option>
        {action.choices.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
    );
  }
  return (
    <>
      {action.input === "note" && (
        <input aria-label="Note (optional)" value={text} onChange={(e) => setText(e.target.value)} placeholder="Note (optional)" className={`${FIELD} h-7 w-44 text-xs`} />
      )}
      {action.input === "reason" && (
        <input aria-label={`Why (${action.label.toLowerCase()})`} value={text} onChange={(e) => setText(e.target.value)} placeholder="Why (required)" className={`${FIELD} h-7 w-44 text-xs`} />
      )}
      <button onClick={() => onRun(text)} disabled={action.input === "reason" && !text.trim()}
        className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted disabled:opacity-50">{action.label}</button>
    </>
  );
}
