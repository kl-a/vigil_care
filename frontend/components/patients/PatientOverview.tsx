"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { SectionSlot } from "@/components/SectionSlot";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import { JOB_TITLE_LABEL, isKnownJobTitle, signOffName } from "@/lib/jobTitles";
import {
  changeIdentity, IDENTITY_FIELDS, IDENTITY_LABEL, removePatient, type IdentityChange, type IdentityField, type IdentityHistoryEntry,
  type PatientDetail,
} from "@/lib/patients";
import { formatWhen } from "@/lib/users";
import { usePatient } from "./PatientContext";

/** Patient Overview (design doc §5 screen 4). Stage 2: Patient Identity; later stages add Conditions, Care Team, modules' sections. */
export function PatientOverview() {
  const router = useRouter();
  const me = useSignedInUser();
  const { state, update } = usePatient();
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(false);
  if (state.status !== "ready") return null;
  const { patient } = state;
  return (
    <div className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <section aria-labelledby="patient-identity" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 id="patient-identity" className="m-0 text-sm font-semibold">Patient Identity</h2>
          {!editing && (
            <button onClick={() => setEditing(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Edit details</button>
          )}
        </div>
        {editing ? (
          <IdentityForm patient={patient} onCancel={() => setEditing(false)} onSaved={(next) => { update(next); setEditing(false); }} />
        ) : (
          <dl className="m-0 grid grid-cols-1 gap-x-6 gap-y-1.5 text-[13px] sm:grid-cols-[max-content_1fr_max-content_1fr]">
            {IDENTITY_FIELDS.map(({ key, label, mono }) => (
              <div key={key} className="contents">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className={`m-0 ${mono ? "font-mono text-xs" : ""}`}>{patient.identity[key] ?? "—"}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className="m-0 text-xs text-muted-foreground">
          Shown in full inside Vigil only. It never leaves the Practice; De-identified Exports use the Pseudonym {patient.pseudonym} instead.
        </p>
      </section>
      <SectionSlot slot="patient-overview" />
      <section aria-labelledby="identity-trail" className="flex flex-col gap-2">
        <h2 id="identity-trail" className="m-0 text-sm font-semibold">Audit trail</h2>
        <ol aria-label="Identity audit trail" className="m-0 flex list-none flex-col gap-2 p-0">
          {patient.history.map((entry, index) => <TrailEntry key={index} entry={entry} />)}
        </ol>
      </section>
      <div>
        <button onClick={() => setRemoving(true)} className="h-8 rounded-md border border-border px-3 text-[13px] text-neg hover:bg-muted">Remove Patient</button>
      </div>
      {removing && (
        <ReasonDialog title={`Remove ${patient.display_name}`} actor={signOffName(me)} confirmLabel="Remove Patient" danger
          onConfirm={async (reason) => { await removePatient(patient.id, reason ?? ""); router.push("/patients"); }}
          onClose={() => setRemoving(false)}>
          <p className="m-0 text-[13px] text-muted-foreground">
            For a Patient added by mistake, such as a duplicate. They disappear from the Patient List and search. Nothing is erased: their page will say who removed them and why.
          </p>
        </ReasonDialog>
      )}
    </div>
  );
}

function TrailEntry({ entry }: { entry: IdentityHistoryEntry }) {
  const jobTitle = isKnownJobTitle(entry.by_job_title) ? JOB_TITLE_LABEL[entry.by_job_title] : entry.by_job_title;
  const changes = Object.entries(entry.after ?? {}).map(([field, value]) => ({
    label: IDENTITY_LABEL[field as IdentityField] ?? field,
    before: entry.before?.[field] ?? "—",
    after: value ?? "—",
  }));
  return (
    <li className="rounded-md border border-border bg-card px-3 py-2 text-[13px]">
      <div className="font-medium">{entry.before ? "Identity changed" : "Patient created"}</div>
      {entry.before && (
        <div className="mt-1 flex flex-col text-xs">
          {changes.map((change) => <span key={change.label}>{change.label}: {String(change.before)} → {String(change.after)}</span>)}
        </div>
      )}
      <div className="text-xs text-muted-foreground">Signed off by {entry.by_display_name} ({jobTitle}) · {formatWhen(entry.at)}</div>
      {entry.reason && <div className="mt-1 text-xs">Reason: {entry.reason}</div>}
    </li>
  );
}

function IdentityForm({ patient, onSaved, onCancel }: { patient: PatientDetail; onSaved: (next: PatientDetail) => void; onCancel: () => void }) {
  const [draft, setDraft] = useState(() =>
    Object.fromEntries(IDENTITY_FIELDS.map(({ key }) => [key, patient.identity[key] ?? ""])) as Record<IdentityField, string>,
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    // Only what changed is sent; the backend records it as one Verification with before/after.
    const change: Record<string, string> = {};
    for (const { key } of IDENTITY_FIELDS) {
      if (draft[key].trim() !== (patient.identity[key] ?? "")) change[key] = draft[key].trim();
    }
    if (Object.keys(change).length === 0) { onCancel(); return; }
    setBusy(true);
    setError(null);
    try {
      onSaved(await changeIdentity(patient.id, change as IdentityChange));
    } catch (reason) {
      setError(messageOf(reason));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="Edit Patient Identity" className="flex flex-col gap-3">
      <IdentityFields draft={draft} onChange={setDraft} />
      <p className="m-0 text-xs text-muted-foreground">Recorded in the Patient&apos;s audit trail under your name.</p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        <button type="submit" disabled={busy} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">Save details</button>
      </div>
    </form>
  );
}

/** The Patient Identity inputs, shared by "New Patient" and "Edit details". */
export function IdentityFields({ draft, onChange }: { draft: Record<IdentityField, string>; onChange: (draft: Record<IdentityField, string>) => void }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
      {IDENTITY_FIELDS.map(({ key, label, required, type, mono, hint }) => (
        <label key={key} className={`flex flex-col gap-1 text-xs font-medium ${key === "address" ? "sm:col-span-2" : ""}`}>
          {label}
          <input type={type ?? "text"} value={draft[key]} required={required}
            onChange={(e) => onChange({ ...draft, [key]: e.target.value })} className={`${FIELD} ${mono ? "font-mono" : ""}`} />
          {hint && <span className="text-[11px] font-normal text-muted-foreground">{hint}</span>}
        </label>
      ))}
    </div>
  );
}
