"use client";

import { useEffect, useState, type FormEvent } from "react";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import { changePractice, fetchPractice, type PracticeChange, type PracticeDetails } from "@/lib/practice";

type Draft = Record<"name" | "address" | "phone" | "fax" | "email" | "abn", string>;

const FIELDS: { key: keyof Draft; label: string; hint?: string; wide?: boolean }[] = [
  { key: "name", label: "Practice name", wide: true },
  { key: "address", label: "Registered address", hint: "Where the Practice sees Patients is under Sites.", wide: true },
  { key: "phone", label: "Phone" },
  { key: "fax", label: "Fax" },
  { key: "email", label: "Email" },
  { key: "abn", label: "ABN", hint: "11 digits" },
];

function toDraft(practice: PracticeDetails): Draft {
  const text = (value: string | null | undefined) => value ?? "";
  return {
    name: practice.name, address: text(practice.address), phone: text(practice.phone), fax: text(practice.fax),
    email: text(practice.email), abn: text(practice.abn),
  };
}

/** Only what changed is sent; the backend records it as one Verification with before/after. */
function changesBetween(saved: Draft, draft: Draft): PracticeChange {
  const change: PracticeChange = {};
  for (const { key } of FIELDS) {
    if (draft[key].trim() !== saved[key].trim()) change[key] = draft[key].trim();
  }
  return change;
}

export function PracticeDetailsForm({ canEdit }: { canEdit: boolean }) {
  const [saved, setSaved] = useState<Draft | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState<{ kind: "saved" | "error"; message: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchPractice()
      .then((practice) => { const d = toDraft(practice); setSaved(d); setDraft(d); })
      .catch((reason: unknown) => setStatus({ kind: "error", message: messageOf(reason) }));
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!saved || !draft) return;
    const change = changesBetween(saved, draft);
    if (Object.keys(change).length === 0) { setStatus({ kind: "saved", message: "Nothing changed." }); return; }
    setBusy(true);
    try {
      const next = toDraft(await changePractice(change));
      setSaved(next);
      setDraft(next);
      setStatus({ kind: "saved", message: "Saved. The change is in the audit trail under your name." });
    } catch (reason) {
      setStatus({ kind: "error", message: messageOf(reason) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="practice-details" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <h2 id="practice-details" className="m-0 text-sm font-semibold">Practice details</h2>
      {!draft && !status && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {draft && (
        <form onSubmit={save} aria-label="Practice details" className="flex flex-col gap-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {FIELDS.map(({ key, label, hint, wide }) => (
              <label key={key} className={`flex flex-col gap-1 text-xs font-medium ${wide ? "sm:col-span-2" : ""}`}>
                {label}
                <input
                  id={`practice-${key}`}
                  value={draft[key]}
                  readOnly={!canEdit}
                  required={key === "name"}
                  onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
                  className={`${FIELD} ${canEdit ? "" : "bg-muted"}`}
                />
                {hint && <span className="text-[11px] font-normal text-muted-foreground">{hint}</span>}
              </label>
            ))}
          </div>
          {canEdit ? (
            <div className="flex items-center justify-end gap-3">
              {status && <span role={status.kind === "error" ? "alert" : "status"} className={`text-xs ${status.kind === "error" ? "text-neg" : "text-muted-foreground"}`}>{status.message}</span>}
              <button type="submit" disabled={busy} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">Save details</button>
            </div>
          ) : (
            <p className="m-0 text-xs text-muted-foreground">Only clinicians and developer admins change the Practice&apos;s details.</p>
          )}
        </form>
      )}
      {!draft && status?.kind === "error" && <p role="alert" className="m-0 text-[13px] text-neg">{status.message}</p>}
    </section>
  );
}
