"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { useSignedInUser, useViewer } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import {
  addCondition, changeCondition, changesBetween, CONDITION_STATUS_LABEL, fetchConditions, fetchEntryRights, removeCondition,
  type ConditionRow, type ConditionStatus, type Entered,
} from "@/lib/clinical";
import { JOB_TITLE_LABEL, isKnownJobTitle, signOffName } from "@/lib/jobTitles";
import { conditionExtensionsFor } from "@/lib/modules/registry";
import type { ConditionExtension } from "@/lib/modules/types";
import { formatWhen } from "@/lib/users";

type Values = { name: string; status: ConditionStatus; onset_date: string; notes: string };
const EMPTY: Values = { name: "", status: "active", onset_date: "", notes: "" };

function valuesOf(row: ConditionRow): Values {
  return { name: row.name, status: row.status, onset_date: row.onset_date ?? "", notes: row.notes ?? "" };
}

/** An empty date or note is sent as null (cleared), never as "". */
function apiValues(values: Values) {
  return { ...values, name: values.name.trim(), onset_date: values.onset_date || null, notes: values.notes.trim() || null };
}

/**
 * Conditions (#35, design doc §5 screens 4 and 9): any diagnosed condition, active or resolved, entered by hand.
 * Adding is signed off by the User; a correction or removal says why, once per save.
 */
export function Conditions({ patientId }: { patientId: string }) {
  const me = useSignedInUser();
  const { modules } = useViewer();
  const [rows, setRows] = useState<ConditionRow[] | null>(null);
  const [rights, setRights] = useState<Record<string, boolean>>({});
  const canEnter = Boolean(rights.condition);
  // A module's Condition extension, offered to those who may record one.
  const extensions = conditionExtensionsFor(modules).filter((extension) => rights[extension.factKind]);
  const [extension, setExtension] = useState<ConditionExtension | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<ConditionRow | null>(null);
  const [saving, setSaving] = useState<{ row: ConditionRow; values: Values } | null>(null);
  const [removing, setRemoving] = useState<ConditionRow | null>(null);

  const load = useCallback(() => {
    fetchConditions(patientId).then(setRows).catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId]);
  useEffect(load, [load]);
  useEffect(() => {
    fetchEntryRights().then(setRights).catch(() => setRights({}));
  }, []);

  return (
    <section aria-labelledby="conditions" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id="conditions" className="m-0 text-sm font-semibold">Conditions</h2>
        {canEnter ? (
          !adding && <button onClick={() => { setAdding(true); setEditing(null); }} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Add Condition</button>
        ) : (
          <EntryLock />
        )}
      </div>
      {adding && extensions.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {extensions.map((option) => (
            <label key={option.factKind} className="inline-flex items-center gap-1.5 text-[13px]">
              <input type="checkbox" checked={extension === option} onChange={(e) => setExtension(e.target.checked ? option : null)} />
              {option.label}
            </label>
          ))}
        </div>
      )}
      {adding && extension && (
        <extension.Form patientId={patientId} onCancel={() => { setAdding(false); setExtension(null); }}
          onSaved={() => { setAdding(false); setExtension(null); load(); }} />
      )}
      {adding && !extension && (
        <ConditionForm label="New Condition" submitLabel="Add Condition" initial={EMPTY} onCancel={() => setAdding(false)}
          onSubmit={async (values) => { await addCondition(patientId, apiValues(values)); setAdding(false); load(); }} />
      )}
      {editing && (
        <ConditionForm label={`Edit ${editing.name}`} submitLabel="Save" initial={valuesOf(editing)} onCancel={() => setEditing(null)}
          onSubmit={async (values) => {
            // Nothing changed: nothing to sign off, so no reason to ask for.
            if (Object.keys(changesBetween(apiValues(valuesOf(editing)), apiValues(values))).length === 0) setEditing(null);
            else setSaving({ row: editing, values });
          }} />
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {rows === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Conditions…</p>}
      {rows?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {rows && rows.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border">
          <table aria-label="Conditions" className="w-full border-collapse text-[13px]">
            <thead className="bg-muted text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Condition</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Onset</th>
                <th className="px-3 py-2 font-medium">Entered by</th>
                {canEnter && <th className="px-3 py-2 font-medium"><span className="sr-only">Actions</span></th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-border align-top">
                  <td className="px-3 py-2">
                    <div className="font-medium">{row.name}</div>
                    {row.notes && <div className="text-xs text-muted-foreground">{row.notes}</div>}
                  </td>
                  <td className="px-3 py-2"><StatusPill tone={row.status === "active" ? "cau" : "neu"}>{CONDITION_STATUS_LABEL[row.status]}</StatusPill></td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDate(row.onset_date)}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground"><EnteredBy entered={row.entered} /></td>
                  {canEnter && row.extended_by_module && (
                    <td className="px-3 py-2 text-right text-xs text-muted-foreground">
                      {modules.active_modules.includes(row.extended_by_module) ? "Changed in its own sub-tab" : "Read-only: its module isn't active"}
                    </td>
                  )}
                  {canEnter && !row.extended_by_module && (
                    <td className="whitespace-nowrap px-3 py-2 text-right">
                      <span className="inline-flex gap-2">
                        <button onClick={() => { setEditing(row); setAdding(false); }} className="text-xs font-medium text-primary">Edit</button>
                        <button onClick={() => setRemoving(row)} className="text-xs font-medium text-neg">Remove</button>
                      </span>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {saving && (
        <ReasonDialog title={`Save changes to ${saving.row.name}`} actor={signOffName(me)} confirmLabel="Save"
          onConfirm={async (reason) => {
            const changes = changesBetween(apiValues(valuesOf(saving.row)), apiValues(saving.values));
            await changeCondition(patientId, saving.row.id, { ...changes, reason: reason ?? "" });
            setSaving(null); setEditing(null); load();
          }}
          onClose={() => setSaving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">Say why you&apos;re changing it, once for this save. The old and new values are kept in the audit trail.</p>
        </ReasonDialog>
      )}
      {removing && (
        <ReasonDialog title={`Remove ${removing.name}`} actor={signOffName(me)} confirmLabel="Remove Condition" danger
          onConfirm={async (reason) => { await removeCondition(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">For a Condition recorded by mistake. It leaves the record; the audit trail keeps what it was, who removed it and why.</p>
        </ReasonDialog>
      )}
    </section>
  );
}

/** Who entered a value, their Job Title then, and when. */
export function EnteredBy({ entered }: { entered: Entered | null }) {
  if (!entered) return <>—</>;
  const jobTitle = isKnownJobTitle(entered.job_title) ? JOB_TITLE_LABEL[entered.job_title] : entered.job_title;
  return <>{entered.by} ({jobTitle}), {formatWhen(entered.at)}</>;
}

function ConditionForm({ label, submitLabel, initial, onCancel, onSubmit }: {
  label: string;
  submitLabel: string;
  initial: Values;
  onCancel: () => void;
  onSubmit: (values: Values) => Promise<void>;
}) {
  const [values, setValues] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const set = (field: keyof Values) => (value: string) => setValues((current) => ({ ...current, [field]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await onSubmit(values);
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  return (
    <form aria-label={label} onSubmit={submit} className="flex flex-col gap-3 rounded-md border border-border bg-background p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[2fr_1fr_1fr]">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Condition
          <input value={values.name} onChange={(e) => set("name")(e.target.value)} required placeholder="e.g. Type 2 diabetes" className={FIELD} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Status
          <select value={values.status} onChange={(e) => set("status")(e.target.value)} className={FIELD}>
            <option value="active">Active</option>
            <option value="resolved">Resolved</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Onset date
          <input type="date" value={values.onset_date} onChange={(e) => set("onset_date")(e.target.value)} className={FIELD} />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs font-medium">
        Notes
        <input value={values.notes} onChange={(e) => set("notes")(e.target.value)} className={FIELD} />
      </label>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">{submitLabel}</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}
