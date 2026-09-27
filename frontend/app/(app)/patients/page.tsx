"use client";

import { CircleDot } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { IdentityFields } from "@/components/patients/PatientOverview";
import { useViewer } from "@/components/shell/ViewerProvider";
import { PseudonymChip } from "@/components/ui/PseudonymChip";
import { FIELD } from "@/components/ui/styles";
import { TableCard } from "@/components/ui/TableCard";
import { messageOf } from "@/lib/api";
import { createPatient, IDENTITY_FIELDS, listPatients, type IdentityField, type NewPatient, type PatientRow } from "@/lib/patients";
import { isVisible } from "@/lib/stages";
import { dobParts } from "@/lib/format";
import { patientListColumnsFor } from "@/lib/modules/registry";
import { fetchOpenItems } from "@/lib/summary";
import { formatWhen } from "@/lib/users";

/** Patient List (design doc §5 screen 3, #8). The Cancer Type filter arrives with Stage 4. */
export default function PatientsPage() {
  const router = useRouter();
  const [patients, setPatients] = useState<PatientRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [adding, setAdding] = useState(false);
  const { showUpcoming, modules } = useViewer();
  // Specialty Modules' columns (e.g. Oncology's Cancer Type(s) and Disease Extent) and their filter.
  const moduleColumns = patientListColumnsFor(modules);
  const [moduleValues, setModuleValues] = useState<Record<string, Record<string, string[]>>>({});
  const [filter, setFilter] = useState("");
  useEffect(() => {
    Promise.all(moduleColumns.map((m) => m.load().catch(() => ({}))))
      .then((all) => setModuleValues(all.reduce<Record<string, Record<string, string[]>>>((merged, values) => {
        for (const [patient, cells] of Object.entries(values)) merged[patient] = { ...merged[patient], ...cells };
        return merged;
      }, {})));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- columns follow the active modules
  }, [modules]);
  const filterBy = moduleColumns.find((m) => m.filter)?.filter;
  const filterOptions = filterBy ? [...new Set(Object.values(moduleValues).flatMap((v) => v[filterBy.key] ?? []))].sort() : [];
  const listed = patients?.filter((p) => !filter || !filterBy || (moduleValues[p.id]?.[filterBy.key] ?? []).includes(filter)) ?? null;
  // Open Items per Patient ship with Stage 5 (#48): counted from the Practice's queue.
  const withOpenItems = isVisible({ stage: 5, built: true }, showUpcoming);
  const [openItems, setOpenItems] = useState<Map<string, number> | null>(null);
  useEffect(() => {
    if (!withOpenItems) return;
    fetchOpenItems()
      .then((items) => setOpenItems(items.reduce((counts, i) => counts.set(i.patient_id, (counts.get(i.patient_id) ?? 0) + 1), new Map<string, number>())))
      .catch(() => setOpenItems(null));
  }, [withOpenItems]);

  useEffect(() => {
    listPatients(q).then(setPatients).catch((reason: unknown) => setError(messageOf(reason)));
  }, [q]);

  return (
    <div data-screen-label="Patient List" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="m-0 text-xl font-semibold">Patients</h1>
        <button onClick={() => setAdding(true)} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">New Patient</button>
      </div>
      {adding && (
        <NewPatientForm onCancel={() => setAdding(false)} onCreated={(id) => router.push(`/patients/${id}/overview`)} />
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {patients === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Patients…</p>}
      <TableCard label="Patients" count={listed ? `${listed.length} ${listed.length === 1 ? "patient" : "patients"}` : undefined}
        toolbar={<>
          <input aria-label="Search by name or MRN" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name or MRN" className={`${FIELD} max-w-[340px]`} />
          {filterBy && (
            <label className="flex items-center gap-2 whitespace-nowrap text-xs text-muted-foreground">{filterBy.label}
              <select value={filter} onChange={(e) => setFilter(e.target.value)} className={`${FIELD} w-44`}>
                <option value="">All</option>{filterOptions.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </label>
          )}
        </>}>
      {listed && listed.length === 0 && <p className="m-0 p-3 text-[13px] text-muted-foreground">{q || filter ? "No Patients match." : "No Patients yet."}</p>}
      {listed && listed.length > 0 && (
          <table className="w-full border-collapse text-[13px]">
            <thead className="bg-muted text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">DOB (age)</th>
                <th className="px-3 py-2 font-medium">MRN</th>
                <th className="px-3 py-2 font-medium">Pseudonym</th>
                {moduleColumns.flatMap((m) => m.columns).map((c) => <th key={c.key} className="px-3 py-2 font-medium">{c.label}</th>)}
                {withOpenItems && <th className="px-3 py-2 font-medium">Open Items</th>}
                <th className="px-3 py-2 font-medium">Last updated</th>
              </tr>
            </thead>
            <tbody>
              {listed.map((patient) => (
                <tr key={patient.id} className="border-t border-border">
                  <td className="px-3 py-2"><Link href={`/patients/${patient.id}/overview`} className="font-medium text-primary hover:underline">{patient.display_name}</Link></td>
                  <td className="whitespace-nowrap px-3 py-2"><DobAndAge dob={patient.dob} /></td>
                  <td className="px-3 py-2 font-mono text-xs">{patient.mrn ?? "—"}</td>
                  <td className="px-3 py-2"><PseudonymChip pseudonym={patient.pseudonym} /></td>
                  {moduleColumns.flatMap((m) => m.columns).map((c) => (
                    <td key={c.key} className="px-3 py-2">{moduleValues[patient.id]?.[c.key]?.join("; ") || "—"}</td>
                  ))}
                  {withOpenItems && <td className="px-3 py-2 tabular-nums"><OpenItemCount count={openItems ? openItems.get(patient.id) ?? 0 : undefined} /></td>}
                  <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{formatWhen(patient.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
      )}
      </TableCard>
    </div>
  );
}

/** "29/01/1958 (68)", the age quieter. */
function DobAndAge({ dob }: { dob: string | null | undefined }) {
  if (!dob) return <>—</>;
  const { date, age } = dobParts(dob);
  return <>{date}<span className="text-muted-foreground"> ({age})</span></>;
}

/** A Patient's Open Items: icon and number in the caution tone; a quiet 0 when there are none. */
function OpenItemCount({ count }: { count: number | undefined }) {
  if (count === undefined) return <>—</>;
  if (count === 0) return <span className="text-muted-foreground">0</span>;
  return <span className="inline-flex items-center gap-1 font-medium text-cau"><CircleDot aria-hidden className="h-3.5 w-3.5" />{count}</span>;
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
