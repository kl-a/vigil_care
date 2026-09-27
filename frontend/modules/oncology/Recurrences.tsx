"use client";

import { CircleAlert, CircleCheck, CircleHelp, GitBranch, type LucideIcon } from "lucide-react";
import { useState, type FormEvent } from "react";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { FIELD } from "@/components/ui/styles";
import { messageOf, request, type Schemas } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";
import { formatWhen } from "@/lib/users";
import { CancerDiagnosisForm, type CancerDiagnosisRow } from "./CancerDiagnoses";

export type RecurrenceRow = Schemas["RecurrenceRow"];
type RecurrenceStatus = RecurrenceRow["status"];
type Extent = NonNullable<RecurrenceRow["extent"]>;

export const fetchRecurrences = (patientId: string) => request<RecurrenceRow[]>(`/patients/${patientId}/recurrences`);
export const suspectRecurrence = (patientId: string, diagnosisId: string, body: Schemas["NewRecurrence"]) =>
  request<RecurrenceRow>(`/patients/${patientId}/cancer-diagnoses/${diagnosisId}/recurrences`, { method: "POST", body: JSON.stringify(body) });
export const confirmRecurrence = (patientId: string, id: string) =>
  request<RecurrenceRow>(`/patients/${patientId}/recurrences/${id}/confirm`, { method: "POST" });
export const newPrimaryInstead = (patientId: string, id: string, diagnosis: Schemas["NewCancerDiagnosis"]) =>
  request<RecurrenceRow>(`/patients/${patientId}/recurrences/${id}/new-primary`, { method: "POST", body: JSON.stringify(diagnosis) });
export const ruleOutRecurrence = (patientId: string, id: string, reason: string) =>
  request<RecurrenceRow>(`/patients/${patientId}/recurrences/${id}/rule-out`, { method: "POST", body: JSON.stringify({ reason }) });

/** Each status: its label, colour and icon (colour never works alone, frontend-design principle 6). */
const STATUS: Record<RecurrenceStatus, { label: string; tone: "cau" | "neg" | "neu"; icon: LucideIcon }> = {
  suspected: { label: "Suspected", tone: "cau", icon: CircleHelp },
  confirmed: { label: "Confirmed", tone: "neg", icon: CircleAlert },
  reclassified_as_new_primary: { label: "New primary instead", tone: "neu", icon: GitBranch },
  ruled_out: { label: "Ruled out", tone: "neu", icon: CircleCheck },
};
export const RECURRENCE_STATUS_LABEL = Object.fromEntries(Object.entries(STATUS).map(([k, v]) => [k, v.label])) as Record<RecurrenceStatus, string>;

export function RecurrenceStatus({ status }: { status: RecurrenceStatus }) {
  const { label, tone, icon: Icon } = STATUS[status];
  return <StatusPill tone={tone}><span className="inline-flex items-center gap-1"><Icon aria-hidden className="h-3 w-3" />{label}</span></StatusPill>;
}
const EXTENT_LABEL: Record<Extent, string> = { local: "Local", regional: "Regional", distant: "Distant" };

/** A Cancer Diagnosis's Recurrences (#39): suspected until a clinician confirms, reclassifies or rules one out. */
export function Recurrences({ patientId, diagnosis, recurrences, canRecord, canResolve, onChanged }: {
  patientId: string;
  diagnosis: CancerDiagnosisRow;
  recurrences: RecurrenceRow[];
  canRecord: boolean;
  canResolve: boolean;
  onChanged: () => void;
}) {
  const me = useSignedInUser();
  const [recording, setRecording] = useState(false);
  const [reclassifying, setReclassifying] = useState<RecurrenceRow | null>(null);
  const [rulingOut, setRulingOut] = useState<RecurrenceRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function confirm(recurrence: RecurrenceRow) {
    try { await confirmRecurrence(patientId, recurrence.id); onChanged(); } catch (reason) { setError(messageOf(reason)); }
  }
  return (
    <div className="flex flex-col gap-2 border-t border-border pt-2">
      <div className="flex items-center justify-between gap-2">
        <h4 className="m-0 text-xs font-semibold">Recurrences</h4>
        {canRecord && !recording && <button onClick={() => setRecording(true)} className="text-xs font-medium text-primary">Record a suspected recurrence</button>}
      </div>
      {recording && <SuspectForm onCancel={() => setRecording(false)} onSave={async (body) => { await suspectRecurrence(patientId, diagnosis.id, body); setRecording(false); onChanged(); }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {recurrences.length === 0 && !recording && <p className="m-0 text-xs text-muted-foreground">None recorded.</p>}
      {recurrences.map((r) => (
        <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 text-[13px]">
          <span className="flex flex-col">
            <span>
              <RecurrenceStatus status={r.status} />{" "}
              {r.extent ? EXTENT_LABEL[r.extent] : "Extent not recorded"}{r.sites.length > 0 && `: ${r.sites.join(", ")}`} · detected {formatDate(r.detected_on)}
            </span>
            {r.resolved && (
              <span className="text-xs text-muted-foreground">
                Resolved by {r.resolved.by}, {formatWhen(r.resolved.at)}{r.ruled_out_reason && `: ${r.ruled_out_reason}`}
              </span>
            )}
          </span>
          {r.status === "suspected" && canResolve && (
            <span className="inline-flex gap-2">
              <button onClick={() => confirm(r)} className="text-xs font-medium text-primary">Confirm</button>
              <button onClick={() => setReclassifying(r)} className="text-xs font-medium text-primary">New primary instead</button>
              <button onClick={() => setRulingOut(r)} className="text-xs font-medium text-neg">Rule out</button>
            </span>
          )}
        </div>
      ))}
      {reclassifying && (
        <CancerDiagnosisForm submitLabel="Record the new primary" onCancel={() => setReclassifying(null)}
          prefill={{ dx_date: reclassifying.detected_on ?? "", primary_site: reclassifying.sites[0] ?? "" }}
          onSubmit={async (values) => {
            const body = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, typeof v === "string" ? v.trim() || null : v]));
            await newPrimaryInstead(patientId, reclassifying.id, body as Schemas["NewCancerDiagnosis"]);
            setReclassifying(null); onChanged();
          }} />
      )}
      {rulingOut && (
        <ReasonDialog title="Rule out this recurrence" actor={signOffName(me)} confirmLabel="Rule out"
          onConfirm={async (reason) => { await ruleOutRecurrence(patientId, rulingOut.id, reason ?? ""); setRulingOut(null); onChanged(); }}
          onClose={() => setRulingOut(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">Say why, e.g. what the biopsy showed.</p>
        </ReasonDialog>
      )}
    </div>
  );
}

function SuspectForm({ onCancel, onSave }: { onCancel: () => void; onSave: (body: Schemas["NewRecurrence"]) => Promise<void> }) {
  const [detected, setDetected] = useState("");
  const [extent, setExtent] = useState("");
  const [sites, setSites] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await onSave({
        detected_on: detected || null, extent: (extent || null) as Extent | null,
        sites: sites.split(",").map((s) => s.trim()).filter(Boolean),
      });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  return (
    <form aria-label="Suspected recurrence" onSubmit={submit} className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-background p-3">
      <label className="flex flex-col gap-1 text-xs font-medium">Detected on<input type="date" value={detected} onChange={(e) => setDetected(e.target.value)} className={`${FIELD} w-40`} /></label>
      <label className="flex flex-col gap-1 text-xs font-medium">
        Extent
        <select value={extent} onChange={(e) => setExtent(e.target.value)} className={`${FIELD} w-36`}>
          <option value="">Not recorded</option>{Object.entries(EXTENT_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium">Sites (comma-separated)<input value={sites} onChange={(e) => setSites(e.target.value)} placeholder="e.g. liver, bone" className={`${FIELD} w-60`} /></label>
      {error && <p role="alert" className="m-0 w-full text-[13px] text-neg">{error}</p>}
      <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Record as suspected</button>
      <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
    </form>
  );
}
