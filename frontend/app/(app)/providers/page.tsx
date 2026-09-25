"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { FIELD } from "@/components/ui/styles";
import { StatusPill } from "@/components/ui/StatusPill";
import { messageOf } from "@/lib/api";
import { signOffName } from "@/lib/jobTitles";
import {
  addProvider, changeProvider, deleteProvider, listProviders, SPECIALTIES, SPECIALTY_LABEL,
  type ProviderChange, type ProviderFilters, type ProviderRow, type ProviderSpecialty,
} from "@/lib/providers";

type Placement = "" | "internal" | "external";

/** Provider Management (design doc §5 screen 17, #7): the Practice's directory for Care Teams, letters and referrals. */
export default function ProvidersPage() {
  const me = useSignedInUser();
  const [providers, setProviders] = useState<ProviderRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [specialty, setSpecialty] = useState<ProviderSpecialty | "">("");
  const [placement, setPlacement] = useState<Placement>("");
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<ProviderRow | null>(null);
  const [deleting, setDeleting] = useState<ProviderRow | null>(null);

  const load = useCallback(() => {
    const filters: ProviderFilters = { q, specialty: specialty || undefined, internal: placement ? placement === "internal" : undefined };
    listProviders(filters).then(setProviders).catch((reason: unknown) => setError(messageOf(reason)));
  }, [q, specialty, placement]);
  useEffect(load, [load]);

  return (
    <div data-screen-label="Provider Management" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="m-0 text-xl font-semibold">Provider Management</h1>
        <button onClick={() => { setAdding(true); setEditing(null); }} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">New Provider</button>
      </div>
      <p className="m-0 max-w-[70ch] text-[13px] text-muted-foreground">
        {me.practice_name}&apos;s clinicians, referrers, specialists and trial-site contacts, used for Care Teams, letters and referrals. Every change is recorded under your name.
      </p>
      <div className="flex flex-wrap gap-2">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Search by name
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Grey" className={`${FIELD} w-56`} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Specialty
          <select value={specialty} onChange={(e) => setSpecialty(e.target.value as ProviderSpecialty | "")} className={`${FIELD} w-48`}>
            <option value="">Any specialty</option>
            {SPECIALTIES.map((key) => <option key={key} value={key}>{SPECIALTY_LABEL[key]}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Internal or external
          <select value={placement} onChange={(e) => setPlacement(e.target.value as Placement)} className={`${FIELD} w-40`}>
            <option value="">Both</option>
            <option value="internal">Internal</option>
            <option value="external">External</option>
          </select>
        </label>
      </div>
      {adding && (
        <ProviderForm label="New Provider" submitLabel="Add Provider" onCancel={() => setAdding(false)}
          onSave={async (values) => { await addProvider(values); setAdding(false); load(); }} />
      )}
      {editing && (
        <ProviderForm label={`Edit ${editing.display_name}`} submitLabel="Save Provider" initial={editing} onCancel={() => setEditing(null)}
          onSave={async (values) => { await changeProvider(editing.id, changesFrom(editing, values)); setEditing(null); load(); }} />
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {providers === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Providers…</p>}
      {providers && providers.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">No Providers match.</p>}
      {providers && providers.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="w-full border-collapse text-[13px]">
            <thead className="bg-muted text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">Specialty</th>
                <th className="px-3 py-2 font-medium">Internal / external</th>
                <th className="px-3 py-2 font-medium">Organisation</th>
                <th className="px-3 py-2 font-medium">Provider number</th>
                <th className="px-3 py-2 font-medium">Phone</th>
                <th className="px-3 py-2 font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => (
                <tr key={provider.id} className="border-t border-border align-top">
                  <td className="px-3 py-2">
                    <div className="font-medium">{provider.display_name}</div>
                    {provider.notes && <div className="text-[11px] text-muted-foreground">{provider.notes}</div>}
                  </td>
                  <td className="px-3 py-2">{SPECIALTY_LABEL[provider.specialty]}</td>
                  <td className="px-3 py-2"><StatusPill tone={provider.is_internal ? "pos" : "neu"}>{provider.is_internal ? "Internal" : "External"}</StatusPill></td>
                  <td className="px-3 py-2 text-muted-foreground">{provider.organisation ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{provider.provider_number ?? "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{provider.phone ?? "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    <span className="inline-flex gap-2">
                      <button onClick={() => { setEditing(provider); setAdding(false); }} className="text-xs font-medium text-primary">Edit</button>
                      <button onClick={() => setDeleting(provider)} className="text-xs font-medium text-neg">Delete</button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {deleting && (
        <ReasonDialog title={`Delete ${deleting.display_name}`} actor={signOffName(me)} confirmLabel="Delete Provider" danger
          onConfirm={async (reason) => { await deleteProvider(deleting.id, reason ?? ""); setDeleting(null); load(); }}
          onClose={() => setDeleting(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">They disappear from the directory. Care Teams and letters that name them keep their history.</p>
        </ReasonDialog>
      )}
    </div>
  );
}

type Values = {
  title: string | null; first_name: string; last_name: string; provider_number: string | null; specialty: ProviderSpecialty;
  is_internal: boolean; organisation: string | null; phone: string | null; email: string | null; fax: string | null; notes: string | null;
};

/** Only what changed is sent; the backend records it as one Verification with before/after. */
function changesFrom(provider: ProviderRow, values: Values): ProviderChange {
  const change: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(values)) {
    if (value !== provider[key as keyof ProviderRow]) change[key] = value ?? "";
  }
  return change as ProviderChange;
}

const TEXT_FIELDS: { key: Exclude<keyof Values, "specialty" | "is_internal">; label: string; required?: boolean }[] = [
  { key: "title", label: "Title" },
  { key: "first_name", label: "First name", required: true },
  { key: "last_name", label: "Last name", required: true },
  { key: "provider_number", label: "Provider number" },
  { key: "organisation", label: "Organisation" },
  { key: "phone", label: "Phone" },
  { key: "fax", label: "Fax" },
  { key: "email", label: "Email" },
];

function ProviderForm({ label, submitLabel, initial, onSave, onCancel }: {
  label: string;
  submitLabel: string;
  initial?: ProviderRow;
  onSave: (values: Values) => Promise<void>;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState<Record<string, string>>(() => {
    const text = (value: string | null | undefined) => value ?? "";
    return {
      title: text(initial?.title), first_name: text(initial?.first_name), last_name: text(initial?.last_name),
      provider_number: text(initial?.provider_number), organisation: text(initial?.organisation), phone: text(initial?.phone),
      fax: text(initial?.fax), email: text(initial?.email), notes: text(initial?.notes),
    };
  });
  const [specialty, setSpecialty] = useState<ProviderSpecialty>(initial?.specialty ?? "general_practice");
  const [isInternal, setIsInternal] = useState(initial?.is_internal ?? false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = (key: string) => draft[key]!.trim() || null;
    setBusy(true);
    setError(null);
    try {
      await onSave({
        title: value("title"), first_name: draft.first_name!.trim(), last_name: draft.last_name!.trim(),
        provider_number: value("provider_number"), specialty, is_internal: isInternal, organisation: value("organisation"),
        phone: value("phone"), email: value("email"), fax: value("fax"), notes: value("notes"),
      });
    } catch (reason) {
      setError(messageOf(reason));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label={label} className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <h2 className="m-0 text-sm font-semibold">{label}</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        {TEXT_FIELDS.map(({ key, label: title, required }) => (
          <label key={key} className="flex flex-col gap-1 text-xs font-medium">
            {title}
            <input value={draft[key]} required={required} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
              className={`${FIELD} ${key === "provider_number" ? "font-mono" : ""}`} />
          </label>
        ))}
        <label className="flex flex-col gap-1 text-xs font-medium">
          Specialty
          <select value={specialty} onChange={(e) => setSpecialty(e.target.value as ProviderSpecialty)} className={FIELD}>
            {SPECIALTIES.map((key) => <option key={key} value={key}>{SPECIALTY_LABEL[key]}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 self-end pb-1.5 text-xs font-medium">
          <input type="checkbox" checked={isInternal} onChange={(e) => setIsInternal(e.target.checked)} />
          Internal to the Practice
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium sm:col-span-2">
          Notes
          <input value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} className={FIELD} />
        </label>
      </div>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        <button type="submit" disabled={busy} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">{submitLabel}</button>
      </div>
    </form>
  );
}
