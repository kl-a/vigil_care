"use client";

import { CircleHelp, Minus, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { EnteredBy } from "@/components/clinical/Conditions";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { usePatient } from "@/components/patients/PatientContext";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { FIELD } from "@/components/ui/styles";
import { messageOf, request, type Schemas } from "@/lib/api";
import { fetchEntryRights, fetchImagingStudies, scanName, type ImagingStudyRow } from "@/lib/clinical";
import { formatDate, todayIso } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";
import type { CourseAnnotation, ImagingStudyExtension, TreatmentCourseExtension } from "@/lib/modules/types";
import { fetchCancerDiagnoses, type CancerDiagnosisRow } from "./CancerDiagnoses";

export type ResponseAssessmentRow = Schemas["ResponseAssessmentRow"];
export type Direction = ResponseAssessmentRow["direction"];
type BestResponse = Schemas["BestResponse"];

export const fetchResponseAssessments = (patientId: string) => request<ResponseAssessmentRow[]>(`/patients/${patientId}/response-assessments`);
export const recordResponseAssessment = (patientId: string, body: Schemas["NewResponseAssessment"]) =>
  request<ResponseAssessmentRow>(`/patients/${patientId}/response-assessments`, { method: "POST", body: JSON.stringify(body) });
export const attributeResponseAssessment = (patientId: string, id: string, diagnosisId: string) =>
  request<ResponseAssessmentRow>(`/patients/${patientId}/response-assessments/${id}/attribute`, { method: "POST", body: JSON.stringify({ cancer_diagnosis_id: diagnosisId }) });
export const overrideResponseAssessment = (patientId: string, id: string, direction: Direction, reason: string) =>
  request<ResponseAssessmentRow>(`/patients/${patientId}/response-assessments/${id}/override`, { method: "POST", body: JSON.stringify({ direction, reason }) });
export const removeResponseAssessment = (patientId: string, id: string, reason: string) =>
  request<void>(`/patients/${patientId}/response-assessments/${id}`, { method: "DELETE", body: JSON.stringify({ reason }) });
export const fetchBestResponses = (patientId: string) => request<BestResponse[]>(`/patients/${patientId}/best-responses`);

/** Each direction: its label, colour and icon (colour never works alone, frontend-design principle 6). */
const DIRECTION: Record<Direction, { label: string; tone: "pos" | "neu" | "neg"; icon: LucideIcon }> = {
  responding: { label: "Responding", tone: "pos", icon: TrendingDown },
  stable: { label: "Stable", tone: "neu", icon: Minus },
  progressing: { label: "Progressing", tone: "neg", icon: TrendingUp },
};
const SOURCE_LABEL: Record<ResponseAssessmentRow["source"], string> = { radiology_report: "Radiology report", clinician: "Clinician" };

export function DirectionPill({ direction, prefix }: { direction: Direction; prefix?: string }) {
  const { label, tone, icon: Icon } = DIRECTION[direction];
  return (
    <StatusPill tone={tone}>
      <span className="inline-flex items-center gap-1"><Icon aria-hidden className="h-3 w-3" />{prefix ? `${prefix}: ${label}` : label}</span>
    </StatusPill>
  );
}

/** The ones that count: not overridden by a clinician. */
const counted = (rows: ResponseAssessmentRow[]) => rows.filter((row) => !row.overridden_by_id);

/** Each course's best response on the Core's Treatment Courses: derived, so there's nothing to edit. */
export const bestResponseExtension: TreatmentCourseExtension = {
  load: async (patientId) => {
    const best = await fetchBestResponses(patientId);
    return Object.fromEntries(best.map((b): [string, CourseAnnotation] => [
      b.treatment_course_id,
      { label: `Best Response: ${DIRECTION[b.direction].label}`, detail: b.explanation, overridden: false, badge: <DirectionPill direction={b.direction} prefix="Best Response" /> },
    ]));
  },
};

/** The Response Assessment badge on the Core's Imaging Studies it came from. */
export const responseBadgeExtension: ImagingStudyExtension = {
  load: async (patientId) => {
    const rows = counted(await fetchResponseAssessments(patientId));
    return Object.fromEntries(rows.filter((row) => row.imaging_study_id).map((row) => [row.imaging_study_id!, <DirectionPill key={row.id} direction={row.direction} />]));
  },
};

/** The Response Assessments sub-tab (#43): which way each Cancer Diagnosis is going, over time. */
export function ResponseAssessmentsTab() {
  const { state } = usePatient();
  const patientId = state.status === "ready" ? state.patient.id : null;
  const me = useSignedInUser();
  const [rows, setRows] = useState<ResponseAssessmentRow[] | null>(null);
  const [diagnoses, setDiagnoses] = useState<CancerDiagnosisRow[]>([]);
  const [studies, setStudies] = useState<ImagingStudyRow[]>([]);
  const [rights, setRights] = useState<Record<string, boolean>>({});
  const [recording, setRecording] = useState(false);
  const [overriding, setOverriding] = useState<ResponseAssessmentRow | null>(null);
  const [removing, setRemoving] = useState<ResponseAssessmentRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    if (!patientId) return;
    fetchResponseAssessments(patientId).then(setRows).catch((reason: unknown) => setError(messageOf(reason)));
    fetchCancerDiagnoses(patientId).then(setDiagnoses).catch(() => setDiagnoses([]));
    fetchImagingStudies(patientId).then(setStudies).catch(() => setStudies([]));
  }, [patientId]);
  useEffect(load, [load]);
  useEffect(() => { fetchEntryRights().then(setRights).catch(() => setRights({})); }, []);
  if (!patientId) return null;
  const canRecord = Boolean(rights.response_assessment);
  const isClinician = Boolean(rights.response_assessment_override);
  const scans = Object.fromEntries(studies.map((s) => [s.id, `${scanName(s)}, ${formatDate(s.study_date)}`]));
  async function attribute(row: ResponseAssessmentRow, diagnosisId: string) {
    try { await attributeResponseAssessment(patientId!, row.id, diagnosisId); load(); } catch (reason) { setError(messageOf(reason)); }
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="m-0 text-xs text-muted-foreground">Newest first. A course&apos;s Best Response is shown on its Treatment Course.</p>
        {canRecord ? !recording && <button onClick={() => setRecording(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Record assessment</button> : <EntryLock />}
      </div>
      {recording && (
        <AssessmentForm diagnoses={diagnoses} studies={studies} asClinician={isClinician} onCancel={() => setRecording(false)}
          onSave={async (body) => { await recordResponseAssessment(patientId, body); setRecording(false); load(); }} />
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {rows?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {rows && rows.length > 0 && (
        <ol aria-label="Response Assessments" className="m-0 flex list-none flex-col divide-y divide-border p-0">
          {rows.map((row) => (
            <li key={row.id} className={`flex flex-wrap items-center justify-between gap-2 py-2 text-[13px] ${row.overridden_by_id ? "text-muted-foreground" : ""}`}>
              <span className="flex flex-col gap-0.5">
                <span className="flex flex-wrap items-center gap-2">
                  <DirectionPill direction={row.direction} />
                  {row.cancer_diagnosis_name ?? <StatusPill tone="cau"><span className="inline-flex items-center gap-1"><CircleHelp aria-hidden className="h-3 w-3" />Not sure which Cancer Diagnosis</span></StatusPill>}
                  <span>· {formatDate(row.assessed_on)}</span>
                  {row.overridden_by_id && <span className="text-xs">(overridden by a clinician)</span>}
                </span>
                <span className="text-xs text-muted-foreground">
                  {SOURCE_LABEL[row.source]}{row.imaging_study_id && scans[row.imaging_study_id] && ` · ${scans[row.imaging_study_id]}`}
                  {row.override_reason && ` · Overrode the report: ${row.override_reason}`}
                  {" · Entered by "}<EnteredBy entered={row.entered} />
                </span>
              </span>
              <span className="inline-flex items-center gap-2">
                {isClinician && !row.cancer_diagnosis_id && diagnoses.length > 0 && (
                  <select aria-label="Attribute to" value="" onChange={(e) => e.target.value && attribute(row, e.target.value)} className={`${FIELD} h-7 w-44 text-xs`}>
                    <option value="">Attribute to…</option>
                    {diagnoses.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                )}
                {isClinician && !row.overridden_by_id && <button onClick={() => setOverriding(row)} className="text-xs font-medium text-primary">Override</button>}
                {(row.source === "clinician" ? isClinician : canRecord) && <button onClick={() => setRemoving(row)} className="text-xs font-medium text-neg">Remove</button>}
              </span>
            </li>
          ))}
        </ol>
      )}
      {overriding && <OverrideDialog row={overriding} actor={signOffName(me)} onClose={() => setOverriding(null)}
        onOverride={async (direction, reason) => { await overrideResponseAssessment(patientId, overriding.id, direction, reason); setOverriding(null); load(); }} />}
      {removing && (
        <ReasonDialog title="Remove this Response Assessment" actor={signOffName(me)} confirmLabel="Remove" danger
          onConfirm={async (reason) => { await removeResponseAssessment(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">For one recorded by mistake. To disagree with a report, override it instead.</p>
        </ReasonDialog>
      )}
    </div>
  );
}

function OverrideDialog({ row, actor, onClose, onOverride }: {
  row: ResponseAssessmentRow; actor: string; onClose: () => void; onOverride: (direction: Direction, reason: string) => Promise<void>;
}) {
  const [direction, setDirection] = useState<Direction>(row.direction === "stable" ? "progressing" : "stable");
  return (
    <ReasonDialog title="Override this Response Assessment" actor={actor} confirmLabel="Override" onConfirm={async (reason) => onOverride(direction, reason ?? "")} onClose={onClose}>
      <p className="m-0 text-[13px] text-muted-foreground">Your assessment counts instead, for the same date and scan. The original stays on record.</p>
      <label className="flex flex-col gap-1 text-xs font-medium">
        Your assessment
        <select value={direction} onChange={(e) => setDirection(e.target.value as Direction)} className={FIELD}>
          {Object.entries(DIRECTION).map(([k, d]) => <option key={k} value={k}>{d.label}</option>)}
        </select>
      </label>
    </ReasonDialog>
  );
}

function AssessmentForm({ diagnoses, studies, asClinician, onCancel, onSave }: {
  diagnoses: CancerDiagnosisRow[]; studies: ImagingStudyRow[]; asClinician: boolean; onCancel: () => void;
  onSave: (body: Schemas["NewResponseAssessment"]) => Promise<void>;
}) {
  // One Cancer Diagnosis: it's that one. Several: the User picks, or says they're not sure which.
  const [diagnosis, setDiagnosis] = useState(diagnoses.length === 1 ? diagnoses[0]!.id : "");
  const [on, setOn] = useState(todayIso());
  const [direction, setDirection] = useState<Direction>("stable");
  const [source, setSource] = useState<ResponseAssessmentRow["source"]>("radiology_report");
  const [study, setStudy] = useState("");
  const [error, setError] = useState<string | null>(null);
  // An assessment from a scan is dated as the scan.
  function pickScan(id: string) {
    setStudy(id);
    const scan = studies.find((s) => s.id === id);
    if (scan) setOn(scan.study_date);
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await onSave({ cancer_diagnosis_id: diagnosis || null, assessed_on: on, direction, source, imaging_study_id: study || null });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  return (
    <form aria-label="New Response Assessment" onSubmit={submit} className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-background p-3">
      <label className="flex flex-col gap-1 text-xs font-medium">
        Cancer Diagnosis
        <select value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} className={`${FIELD} w-52`}>
          <option value="">Not sure which</option>
          {diagnoses.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium">Assessed on<input type="date" required value={on} onChange={(e) => setOn(e.target.value)} className={`${FIELD} w-40`} /></label>
      <label className="flex flex-col gap-1 text-xs font-medium">
        Direction
        <select value={direction} onChange={(e) => setDirection(e.target.value as Direction)} className={`${FIELD} w-36`}>
          {Object.entries(DIRECTION).map(([k, d]) => <option key={k} value={k}>{d.label}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium">
        As stated by
        <select value={source} onChange={(e) => setSource(e.target.value as ResponseAssessmentRow["source"])} className={`${FIELD} w-40`}>
          <option value="radiology_report">Radiology report</option>
          {asClinician && <option value="clinician">Clinician (me)</option>}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium">
        From scan
        <select value={study} onChange={(e) => pickScan(e.target.value)} className={`${FIELD} w-60`}>
          <option value="">None</option>
          {studies.map((s) => <option key={s.id} value={s.id}>{scanName(s)}, {formatDate(s.study_date)}</option>)}
        </select>
      </label>
      {error && <p role="alert" className="m-0 w-full text-[13px] text-neg">{error}</p>}
      <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Record</button>
      <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
    </form>
  );
}
