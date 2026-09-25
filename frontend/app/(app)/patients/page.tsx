"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { IdentityFields } from "@/components/patients/PatientOverview";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import { createPatient, formatDob, IDENTITY_FIELDS, listPatients, type IdentityField, type NewPatient, type PatientRow } from "@/lib/patients";
import { formatWhen } from "@/lib/users";

/** Patient List (design doc §5 screen 3, #8). The Cancer Type filter arrives with Stage 4. */
export default function PatientsPage() {
  const router = useRouter();
  const [patients, setPatients] = useState<PatientRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    listPatients(q).then(setPatients).catch((reason: unknown) => setError(messageOf(reason)));
  }, [q]);

  return (
    <div data-screen-label="Patient List" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="m-0 text-xl font-semibold">Patients</h1>
        <button onClick={() => setAdding(true)} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">New Patient</button>
      </div>
      <label className="flex flex-col gap-1 text-xs font-medium">
        Search by name or MRN
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Citizen" className={`${FIELD} max-w-[340px]`} />
      </label>
      {adding && (
        <NewPatientForm onCancel={() => setAdding(false)} onCreated={(id) => router.push(`/patients/${id}/overview`)} />
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {patients === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Patients…</p>}
      {patients && patients.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">{q ? "No Patients match." : "No Patients yet."}</p>}
      {patients && patients.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="w-full border-collapse text-[13px]">
            <thead className="bg-muted text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">DOB (age)</th>
                <th className="px-3 py-2 font-medium">MRN</th>
                <th className="px-3 py-2 font-medium">Pseudonym</th>
                <th className="px-3 py-2 font-medium">Last updated</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((patient) => (
                <tr key={patient.id} className="border-t border-border">
                  <td className="px-3 py-2"><Link href={`/patients/${patient.id}/overview`} className="font-medium text-foreground">{patient.display_name}</Link></td>
                  <td className="whitespace-nowrap px-3 py-2">{formatDob(patient.dob)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{patient.mrn ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{patient.pseudonym}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{formatWhen(patient.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const EMPTY = Object.fromEntries(IDENTITY_FIELDS.map(({ key }) => [key, ""])) as Record<IdentityField, string>;

function NewPatientForm({ onCreated, onCancel }: { onCreated: (id: string) => void; onCancel: () => void }) {
  const [draft, setDraft] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const filled = Object.fromEntries(Object.entries(draft).map(([key, value]) => [key, value.trim()]).filter(([, value]) => value));
    setBusy(true);
    setError(null);
    try {
      onCreated((await createPatient(filled as NewPatient)).id);
    } catch (reason) {
      setError(messageOf(reason));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="New Patient" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <h2 className="m-0 text-sm font-semibold">New Patient</h2>
      <IdentityFields draft={draft} onChange={setDraft} />
      <p className="m-0 text-xs text-muted-foreground">Vigil assigns the Pseudonym (e.g. VG-0042), used only on De-identified Exports. Identifying details are encrypted in the database.</p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        <button type="submit" disabled={busy} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">Create Patient</button>
      </div>
    </form>
  );
}
