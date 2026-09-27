"use client";

import { TriangleAlert } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { usePatient } from "@/components/patients/PatientContext";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { FIELD } from "@/components/ui/styles";
import { messageOf, request, type Schemas } from "@/lib/api";
import { fetchEntryRights } from "@/lib/clinical";
import { formatDate } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";
import { CancerDiagnosisForm, fetchCancerDiagnoses, recordCancerDiagnosis, type CancerDiagnosisRow } from "./CancerDiagnoses";

export type BiomarkerRow = Schemas["BiomarkerRow"];
export type BiomarkerChipData = Schemas["BiomarkerChip"];
type NewBiomarker = Schemas["NewBiomarker"];

const base = (patientId: string, diagnosisId: string) => `/patients/${patientId}/cancer-diagnoses/${diagnosisId}/biomarkers`;
export const fetchBiomarkers = (patientId: string, diagnosisId: string) => request<BiomarkerRow[]>(base(patientId, diagnosisId));
export const addBiomarker = (patientId: string, diagnosisId: string, biomarker: NewBiomarker) =>
  request<BiomarkerRow>(base(patientId, diagnosisId), { method: "POST", body: JSON.stringify(biomarker) });
export const removeBiomarker = (patientId: string, diagnosisId: string, id: string, reason: string) =>
  request<void>(`${base(patientId, diagnosisId)}/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });
export const moveBiomarker = (patientId: string, diagnosisId: string, id: string, target: string, reason: string) =>
  request<BiomarkerRow>(`${base(patientId, diagnosisId)}/${id}/move`, { method: "POST", body: JSON.stringify({ cancer_diagnosis_id: target, reason }) });

const METHODS = ["IHC", "FISH", "NGS", "PCR", "ctDNA"] as const;
const SPECIMENS: Record<string, string> = { primary: "Primary", metastasis: "Metastasis", liquid_biopsy: "Liquid biopsy" };

/** "HER2", or "EGFR exon 19 deletion": a Biomarker and its variant. */
export function markerName(b: { name: string; variant?: string | null }): string {
  return b.variant ? `${b.name} ${b.variant}` : b.name;
}

/** e.g. "positive (3 IHC score)". */
export function resultText(b: { result?: string | null; value_num?: string | number | null; value_unit?: string | null }): string {
  const value = b.value_num !== null && b.value_num !== undefined ? `${b.value_num}${b.value_unit ? ` ${b.value_unit}` : ""}` : "";
  if (b.result && value) return `${b.result} (${value})`;
  return b.result ?? (value || "—");
}

/**
 * A Biomarker's current result, as a chip. Where results differ, an amber "Results differ" mark: never a cause
 * or an action (Differing Biomarker Results, design doc §6.3).
 */
export function BiomarkerChip({ chip }: { chip: BiomarkerChipData }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${chip.differs ? "border-cau-bd bg-cau-bg text-cau" : "border-border"}`}>
      <span className="font-medium">{markerName(chip)}</span> {resultText(chip)}
      {chip.differs && <><TriangleAlert aria-hidden className="h-3 w-3" /><span>Results differ</span></>}
    </span>
  );
}

/**
 * The Biomarkers sub-tab (#38): each Cancer Diagnosis's full history by marker, specimen and date, never
 * overwritten. Where a marker's results differ they're shown side by side, never interpreted.
 */
export function BiomarkersTab() {
  const { state } = usePatient();
  const patientId = state.status === "ready" ? state.patient.id : null;
  const [diagnoses, setDiagnoses] = useState<CancerDiagnosisRow[] | null>(null);
  const [current, setCurrent] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!patientId) return;
    fetchCancerDiagnoses(patientId).then((rows) => { setDiagnoses(rows); setCurrent((c) => c || rows[0]?.id || ""); })
      .catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId]);
  if (!patientId) return null;
  if (error) return <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>;
  if (diagnoses === null) return <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>;
  if (diagnoses.length === 0) return <p className="m-0 text-[13px] text-muted-foreground">Record a Cancer Diagnosis first: Biomarkers belong to one.</p>;
  return (
    <div className="flex flex-col gap-3">
      {diagnoses.length > 1 && (
        <label className="flex w-fit flex-col gap-1 text-xs font-medium">
          Cancer Diagnosis
          <select value={current} onChange={(e) => setCurrent(e.target.value)} className={`${FIELD} w-72`}>
            {diagnoses.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </label>
      )}
      {current && (
        <BiomarkerHistory key={current} patientId={patientId} diagnosisId={current} others={diagnoses.filter((d) => d.id !== current)}
          onChanged={() => fetchCancerDiagnoses(patientId).then(setDiagnoses).catch((reason: unknown) => setError(messageOf(reason)))} />
      )}
    </div>
  );
}

function BiomarkerHistory({ patientId, diagnosisId, others, onChanged }: {
  patientId: string; diagnosisId: string; others: CancerDiagnosisRow[]; onChanged: () => void;
}) {
  const me = useSignedInUser();
  const [rows, setRows] = useState<BiomarkerRow[] | null>(null);
  const [rights, setRights] = useState<Record<string, boolean>>({});
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<BiomarkerRow | null>(null);
  const [moving, setMoving] = useState<BiomarkerRow | null>(null);
  const [newPrimary, setNewPrimary] = useState<BiomarkerRow | null>(null);
  const [target, setTarget] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    fetchBiomarkers(patientId, diagnosisId).then(setRows).catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId, diagnosisId]);
  useEffect(load, [load]);
  useEffect(() => { fetchEntryRights().then(setRights).catch(() => setRights({})); }, []);
  const canEnter = Boolean(rights.biomarker);
  // Moving a result to another primary is a Cancer Diagnosis decision: clinicians only.
  const canMove = Boolean(rights.cancer_diagnosis) && others.length > 0;
  const canRecordPrimary = Boolean(rights.cancer_diagnosis);

  const groups = new Map<string, BiomarkerRow[]>();
  for (const row of rows ?? []) groups.set(markerName(row).toLowerCase(), [...(groups.get(markerName(row).toLowerCase()) ?? []), row]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="m-0 text-xs text-muted-foreground">Every result is kept; the latest by collection date is current. A wrong one is removed and entered again.</p>
        {canEnter ? !adding && <button onClick={() => setAdding(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Add result</button> : <EntryLock />}
      </div>
      {adding && <BiomarkerForm onCancel={() => setAdding(false)} onSave={async (b) => { await addBiomarker(patientId, diagnosisId, b); setAdding(false); load(); }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {rows?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {[...groups.values()].map((results) => (
        <section key={markerName(results[0]!)} aria-label={markerName(results[0]!)} className="flex flex-col gap-1 rounded-md border border-border p-3 text-[13px]">
          <h3 className="m-0 flex items-center gap-2 text-sm font-semibold">
            {markerName(results[0]!)}
            {results[0]!.differs && (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-cau"><TriangleAlert aria-hidden className="h-3 w-3" />Results differ</span>
            )}
          </h3>
          <table className="w-full border-collapse">
            <thead className="text-left text-xs text-muted-foreground">
              <tr><th className="py-1 pr-3 font-medium">Collected</th><th className="py-1 pr-3 font-medium">Result</th><th className="py-1 pr-3 font-medium">Method</th><th className="py-1 pr-3 font-medium">Specimen</th><th className="py-1 font-medium"><span className="sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
              {results.map((b) => (
                <tr key={b.id} className="border-t border-border align-top">
                  <td className="whitespace-nowrap py-1 pr-3 tabular-nums">{formatDate(b.collected_on)}{b.current && <span className="ml-1 text-xs text-muted-foreground">(current)</span>}</td>
                  <td className="py-1 pr-3">{resultText(b)}</td>
                  <td className="py-1 pr-3">{b.method ?? "—"}</td>
                  <td className="py-1 pr-3">{[b.specimen_site, b.specimen_kind && SPECIMENS[b.specimen_kind]].filter(Boolean).join(", ") || "—"}</td>
                  <td className="whitespace-nowrap py-1 text-right">
                    <span className="inline-flex gap-2">
                      {canRecordPrimary && b.differs && (
                        <button onClick={() => setNewPrimary(b)} className="text-xs font-medium text-primary">Record a new primary</button>
                      )}
                      {canMove && <button onClick={() => { setMoving(b); setTarget(others[0]!.id); }} className="text-xs font-medium text-primary">Move to another primary</button>}
                      {canEnter && <button onClick={() => setRemoving(b)} className="text-xs font-medium text-neg">Remove</button>}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      {newPrimary && (
        <div className="flex flex-col gap-2">
          <p className="m-0 text-xs text-muted-foreground">
            Records a new Cancer Diagnosis, then moves this {markerName(newPrimary)} result to it. The date and site come from the result.
          </p>
          <CancerDiagnosisForm submitLabel="Record the new primary and move the result" onCancel={() => setNewPrimary(null)}
            prefill={{ dx_date: newPrimary.collected_on ?? "", primary_site: newPrimary.specimen_site ?? "" }}
            onSubmit={async (values) => {
              const body = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, typeof v === "string" ? v.trim() || null : v]));
              const created = await recordCancerDiagnosis(patientId, body as Schemas["NewCancerDiagnosis"]);
              await moveBiomarker(patientId, diagnosisId, newPrimary.id, created.id, "Recorded as a new primary");
              setNewPrimary(null); load(); onChanged();
            }} />
        </div>
      )}
      {removing && (
        <ReasonDialog title={`Remove ${markerName(removing)} (${formatDate(removing.collected_on)})`} actor={signOffName(me)} confirmLabel="Remove result" danger
          onConfirm={async (reason) => { await removeBiomarker(patientId, diagnosisId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">Results are never edited: remove a wrong one and enter it again.</p>
        </ReasonDialog>
      )}
      {moving && (
        <ReasonDialog title={`Move ${markerName(moving)} (${formatDate(moving.collected_on)})`} actor={signOffName(me)} confirmLabel="Move result"
          onConfirm={async (reason) => { await moveBiomarker(patientId, diagnosisId, moving.id, target, reason ?? ""); setMoving(null); load(); onChanged(); }}
          onClose={() => setMoving(null)}>
          <label className="flex flex-col gap-1 text-xs font-medium">
            To Cancer Diagnosis
            <select value={target} onChange={(e) => setTarget(e.target.value)} className={FIELD}>
              {others.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </label>
        </ReasonDialog>
      )}
    </div>
  );
}

function BiomarkerForm({ onCancel, onSave }: { onCancel: () => void; onSave: (b: NewBiomarker) => Promise<void> }) {
  const [values, setValues] = useState({ name: "", variant: "", result: "", value_num: "", value_unit: "", method: "", specimen_site: "", specimen_kind: "", collected_on: "", reported_on: "" });
  const [error, setError] = useState<string | null>(null);
  const set = (field: keyof typeof values) => (value: string) => setValues((v) => ({ ...v, [field]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    const body = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v.trim() || null])) as unknown as NewBiomarker;
    try { await onSave(body); } catch (reason) { setError(messageOf(reason)); }
  }
  const text = (field: keyof typeof values, label: string, placeholder = "") => (
    <label className="flex flex-col gap-1 text-xs font-medium">{label}<input value={values[field]} onChange={(e) => set(field)(e.target.value)} placeholder={placeholder} className={FIELD} /></label>
  );
  return (
    <form aria-label="New Biomarker result" onSubmit={submit} className="grid grid-cols-1 gap-3 rounded-md border border-border bg-background p-3 sm:grid-cols-4">
      <label className="flex flex-col gap-1 text-xs font-medium">Biomarker<input required value={values.name} onChange={(e) => set("name")(e.target.value)} placeholder="e.g. HER2, EGFR, PD-L1" className={FIELD} /></label>
      {text("variant", "Variant", "e.g. exon 19 deletion")}
      {text("result", "Result", "e.g. positive, negative, equivocal")}
      <div className="grid grid-cols-2 gap-2">{text("value_num", "Value", "e.g. 60")}{text("value_unit", "Unit", "e.g. % TPS")}</div>
      <label className="flex flex-col gap-1 text-xs font-medium">
        Method
        <select value={values.method} onChange={(e) => set("method")(e.target.value)} className={FIELD}>
          <option value="">Not recorded</option>{METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </label>
      {text("specimen_site", "Specimen site", "e.g. Liver")}
      <label className="flex flex-col gap-1 text-xs font-medium">
        Specimen
        <select value={values.specimen_kind} onChange={(e) => set("specimen_kind")(e.target.value)} className={FIELD}>
          <option value="">Not recorded</option>{Object.entries(SPECIMENS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium">Collected on<input type="date" value={values.collected_on} onChange={(e) => set("collected_on")(e.target.value)} className={FIELD} /></label>
      {error && <p role="alert" className="m-0 text-[13px] text-neg sm:col-span-4">{error}</p>}
      <div className="flex gap-2 sm:col-span-4">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Add result</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}
