"use client";

import { CircleHelp, CirclePause } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { EnteredBy } from "@/components/clinical/Conditions";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { usePatient } from "@/components/patients/PatientContext";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import { changesBetween, fetchEntryRights, fetchTreatmentCourses, type TreatmentCourseRow } from "@/lib/clinical";
import { formatDate, todayIso } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";
import {
  addMedication, CATEGORY_LABEL, CHANGE_LABEL, changeMedication, fetchMedicationChanges, fetchMedications, FREQUENCY_LABEL, howTaken,
  isStopped, removeMedication, restartMedication, ROUTE_LABEL, searchDrugs, STATUS_LABEL, stopMedication,
  type Category, type DrugOption, type Frequency, type MedicationChangeRow, type MedicationRow, type NewMedication, type Route,
} from "@/lib/medications";
import { listProviders, type ProviderRow } from "@/lib/providers";
import { formatWhen } from "@/lib/users";

type View = "active" | "discontinued" | "log";
const BUTTON = "h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted";

/** The drug's name, linked to its PBS Drug Lookup page when it's in the drug reference. */
export function DrugName({ medication }: { medication: MedicationRow }) {
  const code = medication.pbs_item_codes[0];
  return (
    <span className="flex flex-col">
      <span className="font-medium">{medication.drug_name}{medication.brand_name && <span className="font-normal text-muted-foreground"> ({medication.brand_name})</span>}</span>
      <span className="text-xs text-muted-foreground">Entered by <EnteredBy entered={medication.entered} /></span>
      {code ? (
        <Link href={`/pbs/${encodeURIComponent(code)}`} className="w-fit text-xs text-primary underline-offset-2 hover:underline" data-noprint>PBS Drug Lookup</Link>
      ) : (
        !medication.in_drug_reference && <span className="text-xs text-muted-foreground">Not in the drug reference</span>
      )}
    </span>
  );
}

/**
 * Medication Manager (#41, design doc §5 screen 10): the Patient's Medications (active, discontinued) and their
 * change log. Picked from the drug reference or typed in; every change says why. Reconciliation comes in Stage 9.
 */
export function MedicationManager() {
  const { state } = usePatient();
  const patientId = state.status === "ready" ? state.patient.id : null;
  const me = useSignedInUser();
  const [view, setView] = useState<View>("active");
  const [rows, setRows] = useState<MedicationRow[] | null>(null);
  const [log, setLog] = useState<MedicationChangeRow[] | null>(null);
  const [canEnter, setCanEnter] = useState(false);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<MedicationRow | null>(null);
  const [saving, setSaving] = useState<{ row: MedicationRow; change: Partial<Values> } | null>(null);
  const [stopping, setStopping] = useState<MedicationRow | null>(null);
  const [restarting, setRestarting] = useState<MedicationRow | null>(null);
  const [removing, setRemoving] = useState<MedicationRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    if (!patientId) return;
    fetchMedications(patientId).then(setRows).catch((reason: unknown) => setError(messageOf(reason)));
    fetchMedicationChanges(patientId).then(setLog).catch(() => setLog([]));
  }, [patientId]);
  useEffect(load, [load]);
  useEffect(() => { fetchEntryRights().then((r) => setCanEnter(Boolean(r.medication))).catch(() => setCanEnter(false)); }, []);
  if (!patientId) return null;
  const active = rows?.filter((m) => !isStopped(m)) ?? [];
  const stopped = rows?.filter(isStopped) ?? [];
  const done = () => { setSaving(null); setStopping(null); setRestarting(null); setRemoving(null); load(); };
  const tabs: [View, string][] = [["active", `Active (${active.length})`], ["discontinued", `Discontinued (${stopped.length})`], ["log", "Change log"]];

  return (
    <div data-screen-label="Medication Manager" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav aria-label="Medications" className="flex gap-1 border-b border-border" data-noprint>
          {tabs.map(([key, label]) => (
            <button key={key} onClick={() => setView(key)} aria-current={view === key ? "page" : undefined}
              className={`-mb-px border-b-2 px-3 py-1.5 text-[13px] ${view === key ? "border-primary font-medium text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
              {label}
            </button>
          ))}
        </nav>
        <span className="inline-flex items-center gap-2" data-noprint>
          <button onClick={() => window.print()} className={BUTTON}>Print</button>
          {canEnter ? !adding && <button onClick={() => { setAdding(true); setEditing(null); }} className={BUTTON}>Add medication</button> : <EntryLock />}
        </span>
      </div>
      <h2 className="m-0 hidden text-base font-semibold print:block">
        {state.status === "ready" && state.patient.display_name}: {view === "log" ? "Medication change log" : `${view === "active" ? "Active" : "Discontinued"} medications`}, printed {formatDate(todayIso())}
      </h2>
      {adding && <MedicationForm patientId={patientId} onCancel={() => setAdding(false)}
        onSave={async (values, drug) => {
          await addMedication(patientId, { ...values, ...drug, status: "active", source: "doctor_entered" });
          setAdding(false); load();
        }} />}
      {editing && <MedicationForm patientId={patientId} editing={editing} onCancel={() => setEditing(null)}
        onSave={async (values) => {
          const change = changesBetween(valuesOf(editing), values) as Partial<Values>;
          // Nothing changed: nothing to sign off, so no reason to ask for.
          if (Object.keys(change).length > 0) setSaving({ row: editing, change });
          setEditing(null);
        }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {rows === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Medications…</p>}
      {rows && view === "active" && (
        <MedicationTable label="Active medications" rows={active} empty="No active medications recorded." render={(m) => (
          <>
            <td className="px-3 py-2"><DrugName medication={m} /></td>
            <td className="px-3 py-2">{howTaken(m)}{m.status !== "active" && <div className="mt-1"><StatusPill tone="cau"><span className="inline-flex items-center gap-1">{m.status === "on_hold" ? <CirclePause aria-hidden className="h-3 w-3" /> : <CircleHelp aria-hidden className="h-3 w-3" />}{STATUS_LABEL[m.status]}</span></StatusPill></div>}</td>
            <td className="px-3 py-2">{m.indication ?? "—"}{m.category && <div className="text-xs text-muted-foreground">{CATEGORY_LABEL[m.category]}</div>}</td>
            <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDate(m.start_date)}</td>
            <td className="px-3 py-2 text-xs">{m.prescriber_name ?? "—"}{m.treatment_course_name && <div className="text-muted-foreground">Part of {m.treatment_course_name}</div>}</td>
            <td className="whitespace-nowrap px-3 py-2 text-right" data-noprint>
              {canEnter && (
                <span className="inline-flex gap-2">
                  <button onClick={() => { setEditing(m); setAdding(false); }} className="text-xs font-medium text-primary">Change</button>
                  <button onClick={() => setStopping(m)} className="text-xs font-medium text-primary">Stop</button>
                  <button onClick={() => setRemoving(m)} className="text-xs font-medium text-neg">Remove</button>
                </span>
              )}
            </td>
          </>
        )} headings={["Medication", "How taken", "For", "Started", "Prescribed by"]} />
      )}
      {rows && view === "discontinued" && (
        <MedicationTable label="Discontinued medications" rows={stopped} empty="None discontinued." render={(m) => (
          <>
            <td className="px-3 py-2"><DrugName medication={m} /></td>
            <td className="px-3 py-2">{howTaken(m)}</td>
            <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDate(m.start_date)} – {formatDate(m.end_date)}</td>
            <td className="px-3 py-2">{m.reason_discontinued ?? STATUS_LABEL[m.status]}</td>
            <td className="whitespace-nowrap px-3 py-2 text-right" data-noprint>
              {canEnter && <button onClick={() => setRestarting(m)} className="text-xs font-medium text-primary">Restart</button>}
            </td>
          </>
        )} headings={["Medication", "How taken", "Taken", "Why stopped"]} />
      )}
      {view === "log" && log && <ChangeLog rows={log} />}
      {saving && (
        <ReasonDialog title={`Save changes to ${saving.row.drug_name}`} actor={signOffName(me)} confirmLabel="Save"
          onConfirm={async (reason) => { await changeMedication(patientId, saving.row.id, { ...saving.change, reason: reason ?? "" }); done(); }}
          onClose={() => setSaving(null)} />
      )}
      {stopping && <StopDialog medication={stopping} actor={signOffName(me)} onClose={() => setStopping(null)}
        onStop={async (end, reason) => { await stopMedication(patientId, stopping.id, end, reason); done(); }} />}
      {restarting && (
        <ReasonDialog title={`Restart ${restarting.drug_name}`} actor={signOffName(me)} confirmLabel="Restart"
          onConfirm={async (reason) => { await restartMedication(patientId, restarting.id, reason ?? ""); done(); }} onClose={() => setRestarting(null)} />
      )}
      {removing && (
        <ReasonDialog title={`Remove ${removing.drug_name}`} actor={signOffName(me)} confirmLabel="Remove" danger
          onConfirm={async (reason) => { await removeMedication(patientId, removing.id, reason ?? ""); done(); }} onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">For a Medication entered by mistake. If the Patient stopped taking it, use Stop instead.</p>
        </ReasonDialog>
      )}
    </div>
  );
}

function MedicationTable({ label, rows, empty, headings, render }: {
  label: string; rows: MedicationRow[]; empty: string; headings: string[]; render: (m: MedicationRow) => ReactNode;
}) {
  if (rows.length === 0) return <p className="m-0 text-[13px] text-muted-foreground">{empty}</p>;
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table aria-label={label} className="w-full border-collapse text-[13px]">
        <thead className="bg-muted text-left text-xs text-muted-foreground">
          <tr>{headings.map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}<th className="px-3 py-2" data-noprint><span className="sr-only">Actions</span></th></tr>
        </thead>
        <tbody>{rows.map((m) => <tr key={m.id} className="border-t border-border align-top">{render(m)}</tr>)}</tbody>
      </table>
    </div>
  );
}

const FIELD_LABEL: Record<string, string> = {
  dose_amount: "Dose", dose_unit: "Unit", frequency: "Frequency", frequency_detail: "Frequency detail", route: "Route", indication: "For",
  category: "Category", start_date: "Started", end_date: "Stopped", status: "Status", reason_discontinued: "Why stopped", brand_name: "Brand",
  prescribed_by_provider_id: "Prescriber", treatment_course_id: "Treatment Course", notes: "Notes",
};

/** What a change log entry changed, e.g. "Dose: 8 → 4". Ids aren't shown, only that they changed. */
export function whatChanged(entry: Pick<MedicationChangeRow, "change_type" | "previous_value" | "new_value">): string {
  if (entry.change_type === "added") return "Added";
  if (!entry.new_value) return "Removed (entered by mistake)";
  return Object.keys(entry.new_value).map((field) => {
    const label = FIELD_LABEL[field] ?? field;
    if (field.endsWith("_id")) return `${label} changed`;
    const show = (v: unknown) => (v === null || v === undefined || v === "" ? "none" : String(v));
    return `${label}: ${show(entry.previous_value?.[field])} → ${show(entry.new_value![field])}`;
  }).join("; ");
}

function ChangeLog({ rows }: { rows: MedicationChangeRow[] }) {
  if (rows.length === 0) return <p className="m-0 text-[13px] text-muted-foreground">No changes yet.</p>;
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table aria-label="Change log" className="w-full border-collapse text-[13px]">
        <thead className="bg-muted text-left text-xs text-muted-foreground">
          <tr><th className="px-3 py-2 font-medium">When</th><th className="px-3 py-2 font-medium">Medication</th><th className="px-3 py-2 font-medium">Change</th><th className="px-3 py-2 font-medium">Who</th><th className="px-3 py-2 font-medium">Why</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-border align-top">
              <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatWhen(r.at)}</td>
              <td className="px-3 py-2 font-medium">{r.drug_name}</td>
              <td className="px-3 py-2"><span className="font-medium">{CHANGE_LABEL[r.change_type]}</span><div className="text-xs text-muted-foreground">{whatChanged(r)}</div></td>
              <td className="px-3 py-2">{r.by}</td>
              <td className="px-3 py-2">{r.reason ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StopDialog({ medication, actor, onClose, onStop }: { medication: MedicationRow; actor: string; onClose: () => void; onStop: (end: string, reason: string) => Promise<void> }) {
  const [end, setEnd] = useState(todayIso());
  return (
    <ReasonDialog title={`Stop ${medication.drug_name}`} actor={actor} confirmLabel="Stop" onConfirm={async (reason) => onStop(end, reason ?? "")} onClose={onClose}>
      <label className="flex flex-col gap-1 text-xs font-medium">Stopped on<input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className={FIELD} /></label>
      {medication.treatment_course_name && <p className="m-0 text-[13px] text-muted-foreground">{medication.treatment_course_name} carries on; end the course itself on the Clinical Data tab.</p>}
    </ReasonDialog>
  );
}

/** The fields a form edits, as the API takes them. */
type Values = Omit<NewMedication, "drug_reference_id" | "drug_name" | "source" | "status"> & { status?: NewMedication["status"] };
/** Which drug: picked from the drug reference, or typed in. */
type DrugPick = { drug_reference_id: string } | { drug_name: string };

function valuesOf(m: MedicationRow): Values {
  return {
    brand_name: m.brand_name ?? null, dose_amount: m.dose_amount ?? null, dose_unit: m.dose_unit ?? null, frequency: m.frequency ?? null,
    frequency_detail: m.frequency_detail ?? null, route: m.route ?? null, indication: m.indication ?? null, category: m.category ?? null, start_date: m.start_date ?? null,
    prescribed_by_provider_id: m.prescribed_by_provider_id ?? null, treatment_course_id: m.treatment_course_id ?? null, notes: m.notes ?? null,
    // Stopped ones are restarted, not changed; the rest can be put on hold and back.
    ...(isStopped(m) ? {} : { status: m.status as NewMedication["status"] }),
  };
}

function MedicationForm({ patientId, editing, onCancel, onSave }: {
  patientId: string; editing?: MedicationRow; onCancel: () => void; onSave: (values: Values, drug: DrugPick) => Promise<void>;
}) {
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  const [courses, setCourses] = useState<TreatmentCourseRow[]>([]);
  const [freeText, setFreeText] = useState(false);
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<DrugOption[]>([]);
  const [drug, setDrug] = useState<DrugOption | null>(null);
  const [name, setName] = useState("");
  const [v, setV] = useState<Record<string, string>>(() => Object.fromEntries(Object.entries(editing ? valuesOf(editing) : {}).map(([k, x]) => [k, x === null ? "" : String(x)])));
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listProviders().then(setProviders).catch(() => setProviders([])); }, []);
  useEffect(() => { fetchTreatmentCourses(patientId).then(setCourses).catch(() => setCourses([])); }, [patientId]);
  useEffect(() => {
    if (editing || freeText || !query.trim()) { setOptions([]); return; }
    const timer = setTimeout(() => { searchDrugs(query).then(setOptions).catch(() => setOptions([])); }, 250);
    return () => clearTimeout(timer);
  }, [query, freeText, editing]);
  const set = (field: string) => (e: { target: { value: string } }) => setV((all) => ({ ...all, [field]: e.target.value }));
  // A cancer drug links to its Treatment Course.
  const cancer = v.category === "cancer_treatment" || drug?.is_cancer_drug || editing?.is_cancer_drug;
  async function submit(event: FormEvent) {
    event.preventDefault();
    const values: Values = {
      brand_name: v.brand_name?.trim() || null, dose_amount: v.dose_amount || null, dose_unit: v.dose_unit?.trim() || null,
      frequency: (v.frequency || null) as Frequency | null, frequency_detail: v.frequency === "other" ? v.frequency_detail?.trim() || null : null, route: (v.route || null) as Route | null, indication: v.indication?.trim() || null,
      category: (v.category || null) as Category | null, start_date: v.start_date || null, prescribed_by_provider_id: v.prescribed_by_provider_id || null,
      treatment_course_id: cancer ? v.treatment_course_id || null : null, notes: v.notes?.trim() || null,
      ...(editing && v.status ? { status: v.status as NewMedication["status"] } : {}),
    };
    try {
      if (!editing && !drug && !name.trim()) throw new Error("Pick a drug from the drug reference, or type its name.");
      await onSave(values, drug ? { drug_reference_id: drug.id } : { drug_name: name.trim() });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  return (
    <form aria-label={editing ? `Change ${editing.drug_name}` : "New medication"} onSubmit={submit} className="flex flex-col gap-3 rounded-md border border-border bg-card p-3" data-noprint>
      {editing ? <p className="m-0 text-[13px] font-medium">{editing.drug_name}</p> : (
        <div className="flex flex-col gap-2">
          {freeText ? (
            <label className="flex flex-col gap-1 text-xs font-medium">Drug name (not in the drug reference)<input value={name} onChange={(e) => setName(e.target.value)} className={`${FIELD} max-w-md`} /></label>
          ) : drug ? (
            <p className="m-0 text-[13px]"><span className="font-medium">{drug.generic_name}</span>{drug.brand_names.length > 0 && ` (${drug.brand_names.join(", ")})`} <button type="button" onClick={() => setDrug(null)} className="text-xs font-medium text-primary">Change drug</button></p>
          ) : (
            <label className="flex flex-col gap-1 text-xs font-medium">
              Drug (from the PBS drug reference)
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Generic or brand name" className={`${FIELD} max-w-md`} />
              {options.length > 0 && (
                <ul aria-label="Drug reference matches" className="m-0 flex max-w-md list-none flex-col rounded-md border border-border p-0">
                  {options.map((o) => (
                    <li key={o.id}><button type="button" onClick={() => { setDrug(o); setOptions([]); }} className="w-full px-2 py-1 text-left text-[13px] hover:bg-muted">
                      {o.generic_name}{o.brand_names.length > 0 && <span className="text-muted-foreground"> ({o.brand_names.slice(0, 3).join(", ")})</span>}
                    </button></li>
                  ))}
                </ul>
              )}
            </label>
          )}
          <label className="inline-flex items-center gap-1.5 text-[13px]"><input type="checkbox" checked={freeText} onChange={(e) => { setFreeText(e.target.checked); setDrug(null); }} />It&apos;s not in the drug reference</label>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-xs font-medium">Dose<input type="number" min="0" step="any" value={v.dose_amount ?? ""} onChange={set("dose_amount")} className={FIELD} /></label>
          <label className="flex flex-col gap-1 text-xs font-medium">Unit<input value={v.dose_unit ?? ""} onChange={set("dose_unit")} placeholder="mg" className={FIELD} /></label>
        </div>
        <label className="flex flex-col gap-1 text-xs font-medium">Frequency
          <select value={v.frequency ?? ""} onChange={set("frequency")} className={FIELD}><option value="">Not recorded</option>{Object.entries(FREQUENCY_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </label>
        {v.frequency === "other" && (
          <label className="flex flex-col gap-1 text-xs font-medium">How often<input value={v.frequency_detail ?? ""} onChange={set("frequency_detail")} placeholder="e.g. Day 1 and 8 of 21" className={FIELD} /></label>
        )}
        <label className="flex flex-col gap-1 text-xs font-medium">Route
          <select value={v.route ?? ""} onChange={set("route")} className={FIELD}><option value="">Not recorded</option>{Object.entries(ROUTE_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">Started<input type="date" value={v.start_date ?? ""} onChange={set("start_date")} className={FIELD} /></label>
        <label className="flex flex-col gap-1 text-xs font-medium">For (indication)<input value={v.indication ?? ""} onChange={set("indication")} className={FIELD} /></label>
        <label className="flex flex-col gap-1 text-xs font-medium">Category
          <select value={v.category ?? ""} onChange={set("category")} className={FIELD}><option value="">Not recorded</option>{Object.entries(CATEGORY_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">Prescribed by
          <select value={v.prescribed_by_provider_id ?? ""} onChange={set("prescribed_by_provider_id")} className={FIELD}><option value="">Not recorded</option>{providers.map((p) => <option key={p.id} value={p.id}>{p.display_name}</option>)}</select>
        </label>
        {editing && v.status && (
          <label className="flex flex-col gap-1 text-xs font-medium">Status
            <select value={v.status} onChange={set("status")} className={FIELD}>
              {(["active", "on_hold", "unknown"] as const).map((k) => <option key={k} value={k}>{STATUS_LABEL[k]}</option>)}
            </select>
          </label>
        )}
        {cancer && (
          <label className="flex flex-col gap-1 text-xs font-medium">Treatment Course
            <select value={v.treatment_course_id ?? ""} onChange={set("treatment_course_id")} className={FIELD}>
              <option value="">Not part of a course</option>
              {courses.filter((c) => c.modality === "systemic").map((c) => <option key={c.id} value={c.id}>{c.regimen_name ?? "Systemic"} ({formatDate(c.start_date)})</option>)}
            </select>
          </label>
        )}
      </div>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">{editing ? "Save" : "Add medication"}</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}
