"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { FIELD } from "@/components/ui/styles";
import { StatusPill } from "@/components/ui/StatusPill";
import { messageOf } from "@/lib/api";
import {
  addCareTeamMember, CARE_TEAM_ROLE_LABEL, CARE_TEAM_ROLES, changeCareTeamMember, formatDate, todayIso,
  type CareTeamChange, type CareTeamRole, type CareTeamRow,
} from "@/lib/careTeam";
import { listProviders, type ProviderRow } from "@/lib/providers";
import { usePatient } from "./PatientContext";

/**
 * Care Team (#9, design doc §5 screen 4): who is involved in this Patient's care, in what role, since when.
 * Ended memberships show as past. Every add, change or end is recorded under the User's name.
 */
export function CareTeam() {
  const { state, careTeam, careTeamError, reloadCareTeam } = usePatient();
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (state.status !== "ready") return null;
  const patientId = state.patient.id;
  const current = careTeam?.filter((member) => member.is_current) ?? [];
  const past = careTeam?.filter((member) => !member.is_current) ?? [];

  async function change(member: CareTeamRow, body: CareTeamChange) {
    setError(null);
    try {
      await changeCareTeamMember(patientId, member.id, body);
      reloadCareTeam();
    } catch (cause) {
      setError(messageOf(cause));
    }
  }

  return (
    <section aria-labelledby="care-team" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id="care-team" className="m-0 text-sm font-semibold">Care Team</h2>
        {!adding && (
          <button onClick={() => setAdding(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Add to Care Team</button>
        )}
      </div>
      {adding && (
        <AddMemberForm patientId={patientId} onCancel={() => setAdding(false)} onAdded={() => { setAdding(false); reloadCareTeam(); }} />
      )}
      {(error ?? careTeamError) && <p role="alert" className="m-0 text-[13px] text-neg">{error ?? careTeamError}</p>}
      {careTeam === null && !careTeamError && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Care Team…</p>}
      {careTeam && current.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">No one in the Care Team yet.</p>}
      {current.length > 0 && (
        <ul aria-label="Current Care Team" className="m-0 flex list-none flex-col gap-2 p-0">
          {current.map((member) => (
            <MemberItem key={member.id} member={member}
              onMakePrimary={() => change(member, { is_primary: true })}
              onEnd={(endDate) => change(member, { end_date: endDate })} />
          ))}
        </ul>
      )}
      {past.length > 0 && (
        <>
          <h3 className="m-0 text-xs font-semibold text-muted-foreground">Past</h3>
          <ul aria-label="Past Care Team" className="m-0 flex list-none flex-col gap-2 p-0">
            {past.map((member) => <MemberItem key={member.id} member={member} />)}
          </ul>
        </>
      )}
    </section>
  );
}

function MemberItem({ member, onMakePrimary, onEnd }: {
  member: CareTeamRow;
  onMakePrimary?: () => void;
  onEnd?: (endDate: string) => void;
}) {
  const [ending, setEnding] = useState(false);
  const [endDate, setEndDate] = useState(todayIso());
  const dates = member.is_current
    ? member.start_date ? `since ${formatDate(member.start_date)}` : "current"
    : `${member.start_date ? `${formatDate(member.start_date)} ` : ""}until ${formatDate(member.end_date)}`;
  return (
    <li className="flex flex-col gap-2 rounded-md border border-border px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="flex flex-col gap-0.5">
          <span className="flex items-center gap-2 text-[13px]">
            <Link href={`/providers/${member.provider_id}`} className="font-medium text-foreground">{member.provider_name}</Link>
            <span className="text-muted-foreground">{CARE_TEAM_ROLE_LABEL[member.role]}</span>
            {member.is_primary && member.is_current && <StatusPill tone="pos">Primary</StatusPill>}
          </span>
          <span className="text-xs text-muted-foreground">{dates}</span>
          {member.notes && <span className="text-xs">{member.notes}</span>}
        </span>
        {member.is_current && onEnd && (
          <span className="flex gap-1.5">
            {!member.is_primary && onMakePrimary && (
              <button onClick={onMakePrimary} className="h-7 rounded-md border border-border px-2 text-xs hover:bg-muted">Make primary</button>
            )}
            {!ending && <button onClick={() => setEnding(true)} className="h-7 rounded-md border border-border px-2 text-xs hover:bg-muted">End</button>}
          </span>
        )}
      </div>
      {ending && onEnd && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-xs font-medium">
            End date
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={`${FIELD} w-44`} />
          </label>
          <button onClick={() => { onEnd(endDate); setEnding(false); }} disabled={!endDate}
            className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">End membership</button>
          <button onClick={() => setEnding(false)} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        </div>
      )}
    </li>
  );
}

function AddMemberForm({ patientId, onAdded, onCancel }: { patientId: string; onAdded: () => void; onCancel: () => void }) {
  const [providers, setProviders] = useState<ProviderRow[] | null>(null);
  const [providerId, setProviderId] = useState("");
  const [role, setRole] = useState<CareTeamRole>("treating_oncologist");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isPrimary, setIsPrimary] = useState(false);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listProviders().then(setProviders).catch((cause: unknown) => setError(messageOf(cause)));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await addCareTeamMember(patientId, {
        provider_id: providerId, role, is_primary: isPrimary,
        start_date: startDate || null, end_date: endDate || null, notes: notes.trim() || null,
      });
      onAdded();
    } catch (cause) {
      setError(messageOf(cause));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="Add to Care Team" className="flex flex-col gap-3 rounded-md border border-dashed border-border p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Provider
          <select value={providerId} required onChange={(e) => setProviderId(e.target.value)} className={FIELD}>
            <option value="">{providers === null ? "Loading Providers…" : "Choose a Provider"}</option>
            {providers?.map((provider) => <option key={provider.id} value={provider.id}>{provider.display_name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Role
          <select value={role} onChange={(e) => setRole(e.target.value as CareTeamRole)} className={FIELD}>
            {CARE_TEAM_ROLES.map((key) => <option key={key} value={key}>{CARE_TEAM_ROLE_LABEL[key]}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 self-end pb-1.5 text-xs font-medium">
          <input type="checkbox" checked={isPrimary} onChange={(e) => setIsPrimary(e.target.checked)} />
          Primary member
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Start date
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={FIELD} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          End date
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={FIELD} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Notes
          <input value={notes} onChange={(e) => setNotes(e.target.value)} className={FIELD} />
        </label>
      </div>
      <p className="m-0 text-xs text-muted-foreground">Recorded in the audit trail under your name. A Provider not in the directory is added under Providers first.</p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
        <button type="submit" disabled={busy} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">Add to Care Team</button>
      </div>
    </form>
  );
}
