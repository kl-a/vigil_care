"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { FIELD } from "@/components/ui/styles";
import { StatusPill } from "@/components/ui/StatusPill";
import { messageOf } from "@/lib/api";
import { COORDINATES_MUST_BE_NUMBERS, parseCoordinate } from "@/lib/location";
import { addSite, changeSite, deleteSite, listSites, type SiteRow } from "@/lib/sites";

/**
 * Settings → Sites (#25): where the Practice sees Patients. Trial-site distances are measured from each.
 * Clinicians and developer admins manage them; every change is a Verification.
 */
export function Sites({ canEdit, actor }: { canEdit: boolean; actor: string }) {
  const [sites, setSites] = useState<SiteRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<SiteRow | null>(null);
  const [deleting, setDeleting] = useState<SiteRow | null>(null);

  const load = useCallback(() => {
    listSites().then(setSites).catch((cause: unknown) => setError(messageOf(cause)));
  }, []);
  useEffect(load, [load]);

  async function makePrimary(site: SiteRow) {
    setError(null);
    try {
      await changeSite(site.id, { is_primary: true });
      load();
    } catch (cause) {
      setError(messageOf(cause));
    }
  }

  return (
    <section aria-labelledby="sites" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id="sites" className="m-0 text-sm font-semibold">Sites</h2>
        {canEdit && !adding && (
          <button onClick={() => setAdding(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Add Site</button>
        )}
      </div>
      <p className="m-0 max-w-[70ch] text-[13px] text-muted-foreground">
        The places the Practice sees Patients, such as its rooms and a hospital clinic. They share the Practice&apos;s Patients and records; distances to trial sites are measured from each one.
      </p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {sites === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {adding && <SiteForm label="New Site" submitLabel="Add Site" onCancel={() => setAdding(false)}
        onSave={async (site) => { await addSite(site); setAdding(false); load(); }} />}
      {sites && sites.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">No Sites yet. The first one added becomes the primary Site.</p>}
      {sites && sites.length > 0 && (
        <ul aria-label="Sites" className="m-0 flex list-none flex-col gap-2 p-0">
          {sites.map((site) => (
            <li key={site.id} className="flex flex-col gap-2 rounded-md border border-border px-3 py-2">
              {editing?.id === site.id ? (
                <SiteForm label={`Edit ${site.name}`} submitLabel="Save Site" initial={site} onCancel={() => setEditing(null)}
                  onSave={async (change) => { await changeSite(site.id, change); setEditing(null); load(); }} />
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="flex flex-col gap-0.5">
                    <span className="flex items-center gap-2 text-[13px] font-medium">
                      {site.name}
                      {site.is_primary && <StatusPill tone="pos">Primary</StatusPill>}
                    </span>
                    <span className="text-xs text-muted-foreground">{site.address ?? "No address"}</span>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {site.lat !== null && site.lng !== null ? `${site.lat}, ${site.lng}` : "No location: add it for trial-site distances"}
                    </span>
                  </span>
                  {canEdit && (
                    <span className="flex gap-1.5">
                      <button onClick={() => setEditing(site)} className="h-7 rounded-md border border-border px-2 text-xs hover:bg-muted">Edit</button>
                      {!site.is_primary && (
                        <>
                          <button onClick={() => makePrimary(site)} className="h-7 rounded-md border border-border px-2 text-xs hover:bg-muted">Make primary</button>
                          <button onClick={() => setDeleting(site)} className="h-7 rounded-md border border-border px-2 text-xs text-neg hover:bg-muted">Delete</button>
                        </>
                      )}
                    </span>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {!canEdit && <p className="m-0 text-xs text-muted-foreground">Only clinicians and developer admins change the Practice&apos;s Sites.</p>}
      {deleting && (
        <ReasonDialog title={`Delete ${deleting.name}`} actor={actor} confirmLabel="Delete Site" danger
          onConfirm={async (reason) => { await deleteSite(deleting.id, reason ?? ""); setDeleting(null); load(); }}
          onClose={() => setDeleting(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">The Site disappears from Vigil. Nothing recorded there is deleted.</p>
        </ReasonDialog>
      )}
    </section>
  );
}

type SiteFields = { name: string; address: string | null; lat: number | null; lng: number | null };

function SiteForm({ label, submitLabel, initial, onSave, onCancel }: {
  label: string;
  submitLabel: string;
  initial?: SiteRow;
  onSave: (site: SiteFields) => Promise<void>;
  onCancel: () => void;
}) {
  const text = (value: string | number | null | undefined) => (value === null || value === undefined ? "" : String(value));
  const [draft, setDraft] = useState({ name: text(initial?.name), address: text(initial?.address), lat: text(initial?.lat), lng: text(initial?.lng) });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const lat = parseCoordinate(draft.lat);
    const lng = parseCoordinate(draft.lng);
    if (lat === "invalid" || lng === "invalid") { setError(COORDINATES_MUST_BE_NUMBERS); return; }
    setBusy(true);
    setError(null);
    try {
      await onSave({ name: draft.name.trim(), address: draft.address.trim() || null, lat, lng });
    } catch (cause) {
      setError(messageOf(cause));
      setBusy(false);
    }
  }

  const field = (key: keyof typeof draft, title: string, hint?: string) => (
    <label className="flex flex-col gap-1 text-xs font-medium">
      {title}
      <input value={draft[key]} required={key === "name"} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} className={FIELD} />
      {hint && <span className="text-[11px] font-normal text-muted-foreground">{hint}</span>}
    </label>
  );

  return (
    <form onSubmit={submit} aria-label={label} className="flex flex-col gap-3 rounded-md border border-dashed border-border p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {field("name", "Name")}
        {field("address", "Address")}
        {field("lat", "Latitude", "For distances to trial sites, e.g. -33.8688")}
        {field("lng", "Longitude", "e.g. 151.2093")}
      </div>
      <p className="m-0 text-xs text-muted-foreground">Recorded in the audit trail under your name.</p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        <button type="submit" disabled={busy} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">{submitLabel}</button>
      </div>
    </form>
  );
}
