"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatusPill } from "@/components/ui/StatusPill";
import { messageOf } from "@/lib/api";
import { CARE_TEAM_ROLE_LABEL, fetchProviderPatients, formatDate, type ProviderPatientRow } from "@/lib/careTeam";
import { fetchProvider, SPECIALTY_LABEL, type ProviderRow } from "@/lib/providers";

/** A Provider (design doc §5 screen 17 "Provider drawer"): their details and the Patients they're involved with (#9). */
export default function ProviderPage({ params }: { params: { id: string } }) {
  const [provider, setProvider] = useState<ProviderRow | null>(null);
  const [patients, setPatients] = useState<ProviderPatientRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProvider(params.id).then(setProvider).catch((reason: unknown) => setError(messageOf(reason)));
    fetchProviderPatients(params.id).then(setPatients).catch((reason: unknown) => setError(messageOf(reason)));
  }, [params.id]);

  return (
    <div data-screen-label="Provider" className="flex w-full max-w-[1000px] flex-col gap-4 px-5 pb-8 pt-3">
      <Link href="/providers" className="text-xs text-primary">← All Providers</Link>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {!provider && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {provider && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="m-0 text-xl font-semibold">{provider.display_name}</h1>
            <StatusPill tone={provider.is_internal ? "pos" : "neu"}>{provider.is_internal ? "Internal" : "External"}</StatusPill>
          </div>
          <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-[13px]">
            <dt className="text-muted-foreground">Specialty</dt><dd className="m-0">{SPECIALTY_LABEL[provider.specialty]}</dd>
            <dt className="text-muted-foreground">Organisation</dt><dd className="m-0">{provider.organisation ?? "—"}</dd>
            <dt className="text-muted-foreground">Provider number</dt><dd className="m-0 font-mono text-xs">{provider.provider_number ?? "—"}</dd>
            <dt className="text-muted-foreground">Phone</dt><dd className="m-0">{provider.phone ?? "—"}</dd>
            <dt className="text-muted-foreground">Fax</dt><dd className="m-0">{provider.fax ?? "—"}</dd>
            <dt className="text-muted-foreground">Email</dt><dd className="m-0">{provider.email ?? "—"}</dd>
            {provider.notes && <><dt className="text-muted-foreground">Notes</dt><dd className="m-0">{provider.notes}</dd></>}
          </dl>
        </>
      )}
      <section aria-labelledby="provider-patients" className="flex flex-col gap-2">
        <h2 id="provider-patients" className="m-0 text-sm font-semibold">Patients involved with</h2>
        {patients && patients.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">Not in any Patient&apos;s Care Team.</p>}
        {patients && patients.length > 0 && (
          <div className="overflow-x-auto rounded-md border border-border bg-card">
            <table className="w-full border-collapse text-[13px]">
              <thead className="bg-muted text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">Patient</th>
                  <th className="px-3 py-2 font-medium">Role</th>
                  <th className="px-3 py-2 font-medium">Dates</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {patients.map((row) => (
                  <tr key={row.care_team_member_id} className="border-t border-border">
                    <td className="px-3 py-2"><Link href={`/patients/${row.patient_id}/overview`} className="font-medium text-foreground">{row.patient_name}</Link></td>
                    <td className="px-3 py-2">{CARE_TEAM_ROLE_LABEL[row.role]}{row.is_primary && row.is_current ? " (primary)" : ""}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{formatDate(row.start_date)} – {row.end_date ? formatDate(row.end_date) : "now"}</td>
                    <td className="px-3 py-2"><StatusPill tone={row.is_current ? "pos" : "neu"}>{row.is_current ? "Current" : "Past"}</StatusPill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
