"use client";

import { CalendarClock, CircleAlert, CircleHelp, GitCompare, ScanSearch, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { RowMenu } from "@/components/ui/RowMenu";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import { act, ageOf, mayAct, WHO_LABEL, type OpenItem, type OpenItemAction } from "@/lib/summary";

/** Each kind of Open Item's icon (the item names which; frontend-design §4.4: one fixed icon per meaning). */
const ICON: Record<OpenItem["icon"], LucideIcon> = { calendar: CalendarClock, compare: GitCompare, help: CircleHelp, scan: ScanSearch, alert: CircleAlert };

export function OpenItemType({ item }: { item: OpenItem }) {
  const Icon = ICON[item.icon];
  return <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-semibold text-cau"><Icon aria-hidden className="h-3.5 w-3.5" />{item.type_label}</span>;
}

/**
 * An Open Item's actions: the first as its button, any others behind "⋯". One that needs something from the User
 * (a note, a reason, a choice) opens a small popover; one that doesn't acts in one click. Nothing is dismissed.
 * Those the User's Job Title can't take show a "Needs clinician" lock.
 */
export function OpenItemActions({ item, onActed, link = false }: { item: OpenItem; onActed: () => void; link?: boolean }) {
  const me = useSignedInUser();
  const [open, setOpen] = useState<OpenItemAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Where to see it in full, and act on it in the other ways (e.g. a new primary instead).
  const openLink = <Link href={`/patients/${item.patient_id}/${item.open_tab}`} className="text-xs font-medium text-primary">Open</Link>;
  if (!mayAct(item.who, me.job_title)) return <span className="inline-flex items-center gap-2"><EntryLock who="clinician" />{openLink}</span>;
  const [first, ...rest] = item.actions;
  async function run(action: OpenItemAction, value?: string) {
    setError(null);
    try { await act(action, value); setOpen(null); onActed(); } catch (reason) { setError(messageOf(reason)); }
  }
  const start = (action: OpenItemAction) => (action.input === "none" ? void run(action) : setOpen(action));
  return (
    <span className="relative inline-flex items-center gap-1.5" data-noprint>
      {first && (
        <button onClick={() => start(first)}
          className={link ? "text-xs font-medium text-primary" : "h-7 whitespace-nowrap rounded-md border border-border bg-card px-2.5 text-xs font-medium hover:bg-muted"}>
          {first.label}
        </button>
      )}
      {rest.length > 0 && <RowMenu label={item.title} items={rest.map((action) => ({ label: action.label, onSelect: () => start(action) }))} />}
      {openLink}
      {open && <ActionPopover action={open} onCancel={() => { setOpen(null); setError(null); }} onRun={(value) => run(open, value)} error={error} />}
      {!open && error && <span role="alert" className="text-xs text-neg">{error}</span>}
    </span>
  );
}

function ActionPopover({ action, onRun, onCancel, error }: { action: OpenItemAction; onRun: (value?: string) => void; onCancel: () => void; error: string | null }) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.querySelector<HTMLElement>("input, select")?.focus(); }, []);
  const required = action.input === "reason" || action.input === "choose";
  return (
    <div ref={ref} role="dialog" aria-label={action.label} onKeyDown={(e) => e.key === "Escape" && onCancel()}
      className="absolute right-0 top-8 z-30 flex w-72 flex-col gap-2 rounded-md border border-border bg-card p-3 text-left shadow-card">
      {action.input === "choose" && (
        action.choices?.length ? (
          <label className="flex flex-col gap-1 text-xs font-medium">{action.label} to
            <select value={value} onChange={(e) => setValue(e.target.value)} className={FIELD}>
              <option value="">Choose…</option>
              {action.choices.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
        ) : <p className="m-0 text-xs text-muted-foreground">Nothing to {action.label.toLowerCase()} it to yet.</p>
      )}
      {action.input === "note" && (
        <label className="flex flex-col gap-1 text-xs font-medium">Note (optional)<input value={value} onChange={(e) => setValue(e.target.value)} className={FIELD} /></label>
      )}
      {action.input === "reason" && (
        <label className="flex flex-col gap-1 text-xs font-medium">Why (required)<input value={value} onChange={(e) => setValue(e.target.value)} className={FIELD} /></label>
      )}
      {error && <p role="alert" className="m-0 text-xs text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="h-7 rounded-md border border-border px-2.5 text-xs">Cancel</button>
        <button onClick={() => onRun(value)} disabled={required && !value.trim()}
          className="h-7 rounded-md bg-primary px-2.5 text-xs font-medium text-primary-foreground disabled:opacity-50">{action.label}</button>
      </div>
    </div>
  );
}

const WHO = (item: OpenItem) => <span className="whitespace-nowrap rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">{WHO_LABEL[item.who]}</span>;
const key = (item: OpenItem) => `${item.type}:${item.subject_id}`;

/** The Dashboard's queue (#54): one row per Open Item, one line high, one action. */
export function OpenItemTable({ items, onActed }: { items: OpenItem[]; onActed: () => void }) {
  if (items.length === 0) return <p className="m-0 p-3 text-[13px] text-muted-foreground">None: nothing needs acting on.</p>;
  return (
    <table aria-label="Open Items" className="w-full border-collapse text-[13px]">
      <thead className="bg-muted text-left text-xs text-muted-foreground">
        <tr><th className="px-3 py-2 font-medium">Type</th><th className="px-3 py-2 font-medium">Patient</th><th className="px-3 py-2 font-medium">Description</th>
          <th className="px-3 py-2 font-medium">Age</th><th className="px-3 py-2 font-medium">Who can act</th><th className="px-3 py-2"><span className="sr-only">Action</span></th></tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={key(item)} className="border-t border-border">
            <td className="px-3 py-2"><OpenItemType item={item} /></td>
            <td className="max-w-[200px] px-3 py-2"><Link href={`/patients/${item.patient_id}/summary`} className="block truncate font-medium text-primary hover:underline">{item.patient_name}</Link></td>
            {/* The description takes what's left and truncates, so every row stays one line (the rest on hover). */}
            <td className="w-full max-w-0 px-3 py-2"><span title={[item.title, item.detail].filter(Boolean).join(" · ")} className="block truncate">{item.title}</span></td>
            <td className="whitespace-nowrap px-3 py-2 tabular-nums text-muted-foreground">{ageOf(item)}</td>
            <td className="whitespace-nowrap px-3 py-2">{WHO(item)}</td>
            <td className="whitespace-nowrap px-3 py-2 text-right"><OpenItemActions item={item} onActed={onActed} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** One Patient's Open Items as cards (the Summary), each with its action. */
export function OpenItemCards({ items, onActed }: { items: OpenItem[]; onActed: () => void }) {
  if (items.length === 0) return <p className="m-0 text-[13px] text-muted-foreground">None: nothing needs acting on.</p>;
  return (
    <ul aria-label="Open Items" className="m-0 grid list-none grid-cols-1 gap-3 p-0 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <li key={key(item)} className="flex items-start justify-between gap-3 rounded-md border border-cau-bd bg-cau-bg/60 p-3 text-[13px]">
          <span className="flex min-w-0 flex-col gap-1">
            <OpenItemType item={item} />
            <span className="font-medium">{item.title}</span>
            {item.detail && <span className="text-xs text-muted-foreground">{item.detail}</span>}
          </span>
          <OpenItemActions item={item} onActed={onActed} />
        </li>
      ))}
    </ul>
  );
}

/** One Patient's Open Items as a compact list (the Overview): title and one action link. */
export function OpenItemList({ items, onActed }: { items: OpenItem[]; onActed: () => void }) {
  if (items.length === 0) return <p className="m-0 text-[13px] text-muted-foreground">None: nothing needs acting on.</p>;
  return (
    <ul aria-label="Open Items" className="m-0 flex list-none flex-col divide-y divide-border p-0">
      {items.map((item) => {
        const Icon = ICON[item.icon];
        return (
          <li key={key(item)} className="flex items-center justify-between gap-3 py-2 text-[13px]">
            <span className="inline-flex min-w-0 items-center gap-2" title={item.detail ?? undefined}>
              <Icon aria-label={item.type_label} className="h-3.5 w-3.5 flex-none text-cau" /><span className="truncate">{item.title}</span>{WHO(item)}
            </span>
            <OpenItemActions item={item} onActed={onActed} link />
          </li>
        );
      })}
    </ul>
  );
}
