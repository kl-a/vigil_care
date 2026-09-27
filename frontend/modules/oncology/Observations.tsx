"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { usePatient } from "@/components/patients/PatientContext";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { FIELD } from "@/components/ui/styles";
import { messageOf, request, type Schemas } from "@/lib/api";
import { fetchEntryRights } from "@/lib/clinical";
import { formatDate, todayIso } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";

export type PerformanceStatusRow = Schemas["PerformanceStatusRow"];
export type CnsStatusRow = Schemas["CnsStatusRow"];

export const fetchPerformanceStatus = (patientId: string) => request<PerformanceStatusRow[]>(`/patients/${patientId}/performance-status`);
export const addPerformanceStatus = (patientId: string, body: Schemas["NewPerformanceStatus"]) =>
  request<PerformanceStatusRow>(`/patients/${patientId}/performance-status`, { method: "POST", body: JSON.stringify(body) });
export const removePerformanceStatus = (patientId: string, id: string, reason: string) =>
  request<void>(`/patients/${patientId}/performance-status/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });
export const fetchCnsStatus = (patientId: string) => request<CnsStatusRow[]>(`/patients/${patientId}/cns-status`);
export const addCnsStatus = (patientId: string, body: Schemas["NewCnsStatus"]) =>
  request<CnsStatusRow>(`/patients/${patientId}/cns-status`, { method: "POST", body: JSON.stringify(body) });
export const removeCnsStatus = (patientId: string, id: string, reason: string) =>
  request<void>(`/patients/${patientId}/cns-status/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });

/** The latest ECOG (or KPS), as a badge with its date. */
export function EcogBadge({ row }: { row: PerformanceStatusRow }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs">
      <span className="font-semibold">{row.scale} {row.value}</span><span className="text-muted-foreground">{formatDate(row.assessed_on)}</span>
    </span>
  );
}

/** e.g. "CNS disease present: 2 lesions (20/09/2026)". */
export function cnsLine(row: CnsStatusRow): string {
  const when = ` (${formatDate(row.assessed_on)})`;
  if (row.present === false) return `No CNS disease${when}`;
  if (row.present) {
    const count = row.lesion_count !== null && row.lesion_count !== undefined ? `: ${row.lesion_count} lesion${row.lesion_count === 1 ? "" : "s"}` : "";
    return `CNS disease present${count}${when}`;
  }
  return `CNS status unknown${when}`;
}

function usePatientId(): string | null {
  const { state } = usePatient();
  return state.status === "ready" ? state.patient.id : null;
}

/** The Performance Status sub-tab (#44): ECOG (or KPS) over time; the latest is current. */
export function PerformanceStatusTab() {
  const patientId = usePatientId();
  const me = useSignedInUser();
  const [rows, setRows] = useState<PerformanceStatusRow[] | null>(null);
  const [canEnter, setCanEnter] = useState(false);
  const [scale, setScale] = useState<"ECOG" | "KPS">("ECOG");
  const [value, setValue] = useState("");
  const [on, setOn] = useState(todayIso());
  const [removing, setRemoving] = useState<PerformanceStatusRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    if (patientId) fetchPerformanceStatus(patientId).then(setRows).catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId]);
  useEffect(load, [load]);
  useEffect(() => { fetchEntryRights().then((r) => setCanEnter(Boolean(r.performance_status))).catch(() => setCanEnter(false)); }, []);
  if (!patientId) return null;
  async function add(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try { await addPerformanceStatus(patientId!, { scale, value: Number(value), assessed_on: on }); setValue(""); load(); } catch (reason) { setError(messageOf(reason)); }
  }
  return (
    <div className="flex flex-col gap-3">
      {canEnter ? (
        <form aria-label="New performance status" onSubmit={add} className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs font-medium">
            Scale
            <select value={scale} onChange={(e) => setScale(e.target.value as "ECOG" | "KPS")} className={`${FIELD} w-28`}><option>ECOG</option><option>KPS</option></select>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Value
            <input required type="number" min={0} max={scale === "ECOG" ? 5 : 100} step={scale === "ECOG" ? 1 : 10} value={value} onChange={(e) => setValue(e.target.value)} className={`${FIELD} w-24`} />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">Assessed on<input required type="date" value={on} onChange={(e) => setOn(e.target.value)} className={`${FIELD} w-40`} /></label>
          <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Add</button>
        </form>
      ) : <EntryLock />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {rows?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {rows && rows.length > 0 && (
        <ul aria-label="Performance status" className="m-0 flex list-none flex-col divide-y divide-border p-0 text-[13px]">
          {rows.map((row, index) => (
            <li key={row.id} className="flex items-center justify-between gap-2 py-1.5">
              <span><EcogBadge row={row} />{index === 0 && <span className="ml-2 text-xs text-muted-foreground">current</span>}</span>
              {canEnter && <button onClick={() => setRemoving(row)} className="text-xs font-medium text-neg">Remove</button>}
            </li>
          ))}
        </ul>
      )}
      {removing && (
        <ReasonDialog title={`Remove ${removing.scale} ${removing.value} (${formatDate(removing.assessed_on)})`} actor={signOffName(me)} confirmLabel="Remove" danger
          onConfirm={async (reason) => { await removePerformanceStatus(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)} />
      )}
    </div>
  );
}

/** The CNS sub-tab (#44): CNS disease over time; first-class because it gates most trials. */
export function CnsTab() {
  const patientId = usePatientId();
  const me = useSignedInUser();
  const [rows, setRows] = useState<CnsStatusRow[] | null>(null);
  const [canEnter, setCanEnter] = useState(false);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<CnsStatusRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    if (patientId) fetchCnsStatus(patientId).then(setRows).catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId]);
  useEffect(load, [load]);
  useEffect(() => { fetchEntryRights().then((r) => setCanEnter(Boolean(r.cns_status))).catch(() => setCanEnter(false)); }, []);
  if (!patientId) return null;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-end">{canEnter ? !adding && <button onClick={() => setAdding(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Record CNS status</button> : <EntryLock />}</div>
      {adding && <CnsForm onCancel={() => setAdding(false)} onSave={async (body) => { await addCnsStatus(patientId, body); setAdding(false); load(); }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {rows?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {rows && rows.length > 0 && (
        <ul aria-label="CNS status" className="m-0 flex list-none flex-col divide-y divide-border p-0 text-[13px]">
          {rows.map((row) => (
            <li key={row.id} className="flex items-start justify-between gap-2 py-1.5">
              <span className="flex flex-col">
                <span>{cnsLine(row)}</span>
                <span className="text-xs text-muted-foreground">
                  {[row.locations.length > 0 && row.locations.join(", "), row.treated && `treated${row.treatment_type ? ` (${row.treatment_type})` : ""}`,
                    row.symptomatic && "symptomatic", row.on_steroids && `on steroids${row.steroid_dose_mg ? ` ${row.steroid_dose_mg} mg` : ""}`,
                    row.leptomeningeal && "leptomeningeal"].filter(Boolean).join(" · ")}
                </span>
              </span>
              {canEnter && <button onClick={() => setRemoving(row)} className="text-xs font-medium text-neg">Remove</button>}
            </li>
          ))}
        </ul>
      )}
      {removing && (
        <ReasonDialog title={`Remove CNS status (${formatDate(removing.assessed_on)})`} actor={signOffName(me)} confirmLabel="Remove" danger
          onConfirm={async (reason) => { await removeCnsStatus(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)} />
      )}
    </div>
  );
}

type Tri = "" | "yes" | "no";
const triValue = (value: Tri) => (value === "" ? null : value === "yes");

function CnsForm({ onCancel, onSave }: { onCancel: () => void; onSave: (body: Schemas["NewCnsStatus"]) => Promise<void> }) {
  const [on, setOn] = useState(todayIso());
  const [present, setPresent] = useState<Tri>("");
  const [count, setCount] = useState("");
  const [locations, setLocations] = useState("");
  const [flags, setFlags] = useState<Record<string, Tri>>({ treated: "", symptomatic: "", on_steroids: "", leptomeningeal: "" });
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await onSave({
        assessed_on: on, present: triValue(present), lesion_count: count ? Number(count) : null,
        locations: locations.split(",").map((l) => l.trim()).filter(Boolean),
        treated: triValue(flags.treated as Tri), symptomatic: triValue(flags.symptomatic as Tri),
        on_steroids: triValue(flags.on_steroids as Tri), leptomeningeal: triValue(flags.leptomeningeal as Tri),
      });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  const tri = (label: string, value: Tri, onChange: (v: Tri) => void) => (
    <label className="flex flex-col gap-1 text-xs font-medium">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value as Tri)} className={`${FIELD} w-32`}>
        <option value="">Not recorded</option><option value="yes">Yes</option><option value="no">No</option>
      </select>
    </label>
  );
  return (
    <form aria-label="New CNS status" onSubmit={submit} className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-background p-3">
      <label className="flex flex-col gap-1 text-xs font-medium">Assessed on<input required type="date" value={on} onChange={(e) => setOn(e.target.value)} className={`${FIELD} w-40`} /></label>
      {tri("CNS disease present", present, setPresent)}
      <label className="flex flex-col gap-1 text-xs font-medium">Lesions<input type="number" min={0} value={count} onChange={(e) => setCount(e.target.value)} className={`${FIELD} w-24`} /></label>
      <label className="flex flex-col gap-1 text-xs font-medium">Locations (comma-separated)<input value={locations} onChange={(e) => setLocations(e.target.value)} className={`${FIELD} w-60`} /></label>
      {(["treated", "symptomatic", "on_steroids", "leptomeningeal"] as const).map((flag) =>
        <span key={flag}>{tri(flag.replace("_", " ").replace(/^./, (c) => c.toUpperCase()), flags[flag] as Tri, (v) => setFlags((f) => ({ ...f, [flag]: v })))}</span>)}
      {error && <p role="alert" className="m-0 w-full text-[13px] text-neg">{error}</p>}
      <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Save</button>
      <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
    </form>
  );
}
