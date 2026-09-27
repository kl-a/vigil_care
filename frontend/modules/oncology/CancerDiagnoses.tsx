"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { usePatient } from "@/components/patients/PatientContext";
import { useSignedInUser, useViewer } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { FIELD } from "@/components/ui/styles";
import { messageOf, request, type Schemas } from "@/lib/api";
import { changesBetween, fetchEntryRights } from "@/lib/clinical";
import { formatDate } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";
import { isPartShipped, isVisible } from "@/lib/stages";
import { BiomarkerChip, markerName } from "./Biomarkers";
import { cnsLine, EcogBadge, fetchCnsStatus, fetchPerformanceStatus, type CnsStatusRow, type PerformanceStatusRow } from "./Observations";
import { fetchRecurrences, Recurrences, RecurrenceStatus, type RecurrenceRow } from "./Recurrences";

export type CancerDiagnosisRow = Schemas["CancerDiagnosisRow"];
export type CancerTypeOption = Schemas["CancerTypeOption"];
type DiseaseExtent = CancerDiagnosisRow["disease_extent"];
type CancerStatus = CancerDiagnosisRow["cancer_status"];

export const fetchCancerTypes = () => request<CancerTypeOption[]>("/cancer-types");
export const fetchCancerDiagnoses = (patientId: string) => request<CancerDiagnosisRow[]>(`/patients/${patientId}/cancer-diagnoses`);
export const recordCancerDiagnosis = (patientId: string, diagnosis: Schemas["NewCancerDiagnosis"]) =>
  request<CancerDiagnosisRow>(`/patients/${patientId}/cancer-diagnoses`, { method: "POST", body: JSON.stringify(diagnosis) });
export const correctCancerDiagnosis = (patientId: string, id: string, change: Schemas["CancerDiagnosisChange"]) =>
  request<CancerDiagnosisRow>(`/patients/${patientId}/cancer-diagnoses/${id}`, { method: "PATCH", body: JSON.stringify(change) });
export const removeCancerDiagnosis = (patientId: string, id: string, reason: string) =>
  request<void>(`/patients/${patientId}/cancer-diagnoses/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });

export const DISEASE_EXTENT_LABEL: Record<DiseaseExtent, string> = {
  localised: "Localised", locally_advanced: "Locally advanced", metastatic: "Metastatic", unknown: "Unknown",
};
export const CANCER_STATUS_LABEL: Record<CancerStatus, string> = {
  active: "Active", no_evidence_of_disease: "No evidence of disease", unknown: "Unknown",
};

type Values = {
  cancer_type: string; name: string; histology: string; primary_site: string; laterality: string; dx_date: string;
  stage_system: string; stage: string; disease_extent: DiseaseExtent; disease_extent_as_of: string; cancer_status: CancerStatus;
};
const EMPTY: Values = {
  cancer_type: "", name: "", histology: "", primary_site: "", laterality: "", dx_date: "", stage_system: "", stage: "",
  disease_extent: "unknown", disease_extent_as_of: "", cancer_status: "unknown",
};

function valuesOf(row: CancerDiagnosisRow): Values {
  return {
    cancer_type: row.cancer_type.key, name: row.name, histology: row.histology ?? "", primary_site: row.primary_site ?? "",
    laterality: row.laterality ?? "", dx_date: row.dx_date ?? "", stage_system: row.stage_system ?? "", stage: row.stage ?? "",
    disease_extent: row.disease_extent, disease_extent_as_of: row.disease_extent_as_of ?? "", cancer_status: row.cancer_status,
  };
}

/** Empty text is sent as null (cleared), never as "". */
function apiValues(values: Values) {
  return Object.fromEntries(Object.entries(values).map(([key, value]) => [key, typeof value === "string" ? value.trim() || null : value])) as Record<string, string | null>;
}

/**
 * Recording or correcting a Cancer Diagnosis (#37): Cancer Type (keyed to MeSH), Stage **at diagnosis**, and
 * Disease Extent **now**. Clinicians only; the backend refuses anyone else.
 */
export function CancerDiagnosisForm({ initial, prefill, submitLabel, onCancel, onSubmit }: {
  initial?: CancerDiagnosisRow;
  /** Values to start a new one from, e.g. a Suspected Recurrence's date and site (new primary instead). */
  prefill?: Partial<Values>;
  submitLabel: string;
  onCancel: () => void;
  onSubmit: (values: Values) => Promise<void>;
}) {
  const [types, setTypes] = useState<CancerTypeOption[]>([]);
  const [values, setValues] = useState<Values>(initial ? valuesOf(initial) : { ...EMPTY, ...prefill });
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { fetchCancerTypes().then(setTypes).catch((reason: unknown) => setError(messageOf(reason))); }, []);
  const type = types.find((t) => t.key === values.cancer_type);
  const set = (field: keyof Values) => (value: string) => setValues((current) => ({ ...current, [field]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try { await onSubmit(values); } catch (reason) { setError(messageOf(reason)); }
  }
  const text = (field: keyof Values, label: string, placeholder = "") => (
    <label className="flex flex-col gap-1 text-xs font-medium">{label}<input value={values[field]} onChange={(e) => set(field)(e.target.value)} placeholder={placeholder} className={FIELD} /></label>
  );
  return (
    <form aria-label={initial ? `Correct ${initial.name}` : "New Cancer Diagnosis"} onSubmit={submit} className="flex flex-col gap-3 rounded-md border border-border bg-background p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Cancer Type
          <select required disabled={Boolean(initial)} value={values.cancer_type} onChange={(e) => set("cancer_type")(e.target.value)} className={FIELD}>
            <option value="">Choose…</option>
            {types.map((t) => <option key={t.key} value={t.key}>{t.display_name}</option>)}
          </select>
          {type?.mesh_term && <span className="font-normal text-muted-foreground">MeSH: {type.mesh_term}</span>}
        </label>
        {text("name", "Name", type?.display_name ?? "e.g. Breast cancer")}
        {text("histology", "Histology", "e.g. Invasive ductal carcinoma")}
        {text("primary_site", "Primary site")}
        <label className="flex flex-col gap-1 text-xs font-medium">
          Laterality
          <select value={values.laterality} onChange={(e) => set("laterality")(e.target.value)} className={FIELD}>
            <option value="">Not recorded</option><option value="left">Left</option><option value="right">Right</option>
            <option value="bilateral">Bilateral</option><option value="not applicable">Not applicable</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">Date of diagnosis<input type="date" value={values.dx_date} onChange={(e) => set("dx_date")(e.target.value)} className={FIELD} /></label>
      </div>
      <fieldset className="m-0 grid grid-cols-1 gap-3 border-0 p-0 sm:grid-cols-3">
        <legend className="mb-1 text-xs font-semibold">Stage at diagnosis <span className="font-normal text-muted-foreground">(never updated as the disease changes)</span></legend>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Staging system
          <input list="staging-systems" value={values.stage_system} onChange={(e) => set("stage_system")(e.target.value)} className={FIELD} />
          <datalist id="staging-systems">{(type?.staging_systems ?? ["TNM"]).map((s) => <option key={s} value={s} />)}</datalist>
        </label>
        {text("stage", "Stage", "e.g. IIA or pT2 N1 M0")}
      </fieldset>
      <fieldset className="m-0 grid grid-cols-1 gap-3 border-0 p-0 sm:grid-cols-3">
        <legend className="mb-1 text-xs font-semibold">Now</legend>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Disease Extent
          <select value={values.disease_extent} onChange={(e) => set("disease_extent")(e.target.value)} className={FIELD}>
            {Object.entries(DISEASE_EXTENT_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">As of<input type="date" value={values.disease_extent_as_of} onChange={(e) => set("disease_extent_as_of")(e.target.value)} className={FIELD} /></label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Status
          <select value={values.cancer_status} onChange={(e) => set("cancer_status")(e.target.value)} className={FIELD}>
            {Object.entries(CANCER_STATUS_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </label>
      </fieldset>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">{submitLabel}</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}

/** "Add Condition" → "This is a primary cancer": records the Condition and its Cancer Diagnosis together. */
export function NewPrimaryCancer({ patientId, onSaved, onCancel }: { patientId: string; onSaved: () => void; onCancel: () => void }) {
  return (
    <CancerDiagnosisForm submitLabel="Record Cancer Diagnosis" onCancel={onCancel}
      onSubmit={async (values) => {
        const { cancer_type, ...rest } = apiValues(values);
        await recordCancerDiagnosis(patientId, { cancer_type: cancer_type ?? "", ...rest } as Schemas["NewCancerDiagnosis"]);
        onSaved();
      }} />
  );
}

/** One line of a Cancer Diagnosis: Stage at diagnosis, Disease Extent now. */
export function stageLine(d: CancerDiagnosisRow): string {
  const stage = d.stage ? `Stage ${d.stage}${d.stage_system ? ` (${d.stage_system})` : ""} at diagnosis${d.dx_date ? `, ${formatDate(d.dx_date)}` : ""}` : "Stage not recorded";
  return `${stage} · ${DISEASE_EXTENT_LABEL[d.disease_extent]}${d.disease_extent_as_of ? ` as of ${formatDate(d.disease_extent_as_of)}` : ""}`;
}

/** The Clinical Data tab's Cancer Diagnosis sub-tab: each primary, recorded and corrected by clinicians. */
export function CancerDiagnosesTab() {
  const { state } = usePatient();
  const me = useSignedInUser();
  const patientId = state.status === "ready" ? state.patient.id : null;
  const [rows, setRows] = useState<CancerDiagnosisRow[] | null>(null);
  const [canEnter, setCanEnter] = useState(false);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<CancerDiagnosisRow | null>(null);
  const [saving, setSaving] = useState<{ row: CancerDiagnosisRow; values: Values } | null>(null);
  const [removing, setRemoving] = useState<CancerDiagnosisRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recurrences, setRecurrences] = useState<RecurrenceRow[]>([]);
  const [rights, setRights] = useState<Record<string, boolean>>({});
  const load = useCallback(() => {
    if (!patientId) return;
    fetchCancerDiagnoses(patientId).then(setRows).catch((reason: unknown) => setError(messageOf(reason)));
    fetchRecurrences(patientId).then(setRecurrences).catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId]);
  useEffect(load, [load]);
  useEffect(() => {
    fetchEntryRights().then((r) => { setRights(r); setCanEnter(Boolean(r.cancer_diagnosis)); }).catch(() => setCanEnter(false));
  }, []);
  if (!patientId) return null;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="m-0 text-xs text-muted-foreground">Each primary cancer, with its Stage at diagnosis and its Disease Extent now.</p>
        {canEnter ? (
          !adding && <button onClick={() => { setAdding(true); setEditing(null); }} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Record a primary cancer</button>
        ) : (
          <EntryLock who="clinician" />
        )}
      </div>
      {adding && <NewPrimaryCancer patientId={patientId} onCancel={() => setAdding(false)} onSaved={() => { setAdding(false); load(); }} />}
      {editing && (
        <CancerDiagnosisForm initial={editing} submitLabel="Save" onCancel={() => setEditing(null)}
          onSubmit={async (values) => {
            if (Object.keys(changesBetween(apiValues(valuesOf(editing)), apiValues(values))).length === 0) setEditing(null);
            else setSaving({ row: editing, values });
          }} />
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {rows?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {rows?.map((d) => (
        <article key={d.id} aria-label={d.name} className="flex flex-col gap-1 rounded-md border border-border p-3 text-[13px]">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="m-0 text-sm font-semibold">{d.name}</h3>
            {canEnter && (
              <span className="inline-flex gap-2">
                <button onClick={() => { setEditing(d); setAdding(false); }} className="text-xs font-medium text-primary">Correct</button>
                <button onClick={() => setRemoving(d)} className="text-xs font-medium text-neg">Remove</button>
              </span>
            )}
          </div>
          <span>{stageLine(d)}</span>
          <span className="text-xs text-muted-foreground">
            {d.cancer_type.display_name}{d.cancer_type.mesh_term && ` (MeSH: ${d.cancer_type.mesh_term})`}{d.histology && ` · ${d.histology}`}
            {d.laterality && ` · ${d.laterality}`} · <StatusPill tone={d.cancer_status === "active" ? "cau" : "neu"}>{CANCER_STATUS_LABEL[d.cancer_status]}</StatusPill>
          </span>
          {d.current_biomarkers.length > 0 && (
            <span className="flex flex-wrap gap-1">{d.current_biomarkers.map((chip) => <BiomarkerChip key={markerName(chip)} chip={chip} />)}</span>
          )}
          <Recurrences patientId={patientId} diagnosis={d} recurrences={recurrences.filter((r) => r.cancer_diagnosis_id === d.id)}
            canRecord={Boolean(rights.recurrence)} canResolve={Boolean(rights.recurrence_attribution)} onChanged={load} />
        </article>
      ))}
      {saving && (
        <ReasonDialog title={`Save changes to ${saving.row.name}`} actor={signOffName(me)} confirmLabel="Save"
          onConfirm={async (reason) => {
            const { cancer_type: _type, ...changes } = changesBetween(apiValues(valuesOf(saving.row)), apiValues(saving.values));
            await correctCancerDiagnosis(patientId, saving.row.id, { ...changes, reason: reason ?? "" } as Schemas["CancerDiagnosisChange"]);
            setSaving(null); setEditing(null); load();
          }}
          onClose={() => setSaving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">Stage is only ever corrected, never updated as the disease changes: record that in Disease Extent. Say why, once for this save.</p>
        </ReasonDialog>
      )}
      {removing && (
        <ReasonDialog title={`Remove ${removing.name}`} actor={signOffName(me)} confirmLabel="Remove Cancer Diagnosis" danger
          onConfirm={async (reason) => { await removeCancerDiagnosis(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">Removes the Cancer Diagnosis and its Condition, for one recorded by mistake. The audit trail keeps what it was.</p>
        </ReasonDialog>
      )}
    </div>
  );
}

/** The Patient Overview's section: one block per Cancer Diagnosis (arrives with Stage 4). */
export function CancerDiagnosisBlocks() {
  const { state } = usePatient();
  const { showUpcoming } = useViewer();
  const patientId = state.status === "ready" ? state.patient.id : null;
  const shown = isVisible({ stage: 4, built: true }, showUpcoming);
  const [rows, setRows] = useState<CancerDiagnosisRow[] | null>(null);
  const [latest, setLatest] = useState<{ ecog?: PerformanceStatusRow; cns?: CnsStatusRow }>({});
  const [recurrences, setRecurrences] = useState<RecurrenceRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!patientId || !shown) return;
    fetchCancerDiagnoses(patientId).then(setRows).catch((reason: unknown) => setError(messageOf(reason)));
    fetchRecurrences(patientId).then(setRecurrences).catch(() => setRecurrences([]));
    // ECOG and CNS ship with 4c.
    if (isPartShipped("4c", showUpcoming)) {
      Promise.all([fetchPerformanceStatus(patientId), fetchCnsStatus(patientId)])
        .then(([ecog, cns]) => setLatest({ ecog: ecog[0], cns: cns[0] })).catch(() => setLatest({}));
    }
  }, [patientId, shown, showUpcoming]);
  if (!shown) return <p className="text-sm text-muted-foreground">Cancer Type, Stage, Disease Extent and Biomarkers per Cancer Diagnosis.</p>;
  if (error) return <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>;
  if (rows === null) return <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>;
  return (
    <div className="flex flex-col gap-3">
      {(latest.ecog || latest.cns?.present) && (
        <div className="flex flex-wrap gap-2 text-[13px]">
          {latest.ecog && <EcogBadge row={latest.ecog} />}
          {/* The CNS panel only when there's CNS disease (#44). */}
          {latest.cns?.present && <span className="text-muted-foreground">{cnsLine(latest.cns)}</span>}
        </div>
      )}
      {rows.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {rows.map((d) => (
        <div key={d.id} className="flex flex-col gap-1 rounded-md border border-border p-3 text-[13px]">
          <span className="font-semibold">{d.name}</span>
          <span className="text-xs text-muted-foreground">{d.cancer_type.display_name}{d.histology && ` · ${d.histology}`}</span>
          <span>{stageLine(d)}</span>
          {d.current_biomarkers.length > 0 && (
            <span className="flex flex-wrap gap-1">{d.current_biomarkers.map((chip) => <BiomarkerChip key={markerName(chip)} chip={chip} />)}</span>
          )}
          {recurrences.filter((r) => r.cancer_diagnosis_id === d.id).map((r) => (
            <span key={r.id} className="text-xs"><RecurrenceStatus status={r.status} /> {r.sites.join(", ") || "site not recorded"} · {formatDate(r.detected_on)}</span>
          ))}
        </div>
      ))}
      </div>
    </div>
  );
}
