"use client";

import { CircleDot, MapPin } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useBreadcrumbLabel } from "@/components/shell/Breadcrumbs";
import { useViewer } from "@/components/shell/ViewerProvider";
import { PseudonymChip } from "@/components/ui/PseudonymChip";
import { CARE_TEAM_ROLE_LABEL } from "@/lib/careTeam";
import { patientHeaderChipsFor } from "@/lib/modules/registry";
import { formatDob } from "@/lib/patients";
import { isVisible } from "@/lib/stages";
import { fetchPatientOpenItems } from "@/lib/summary";
import { usePatient } from "./PatientContext";

const initials = (name: string) => name.replace(/\(.*?\)/g, "").split(/\s+/).filter(Boolean).map((w) => w[0]!.toUpperCase()).slice(0, 2).join("");
/** The suburb, state and postcode: the last part of the address (the street stays on the Overview). */
const suburb = (address: string | null | undefined) => address?.split(",").pop()?.trim() || null;

/**
 * The Patient header band (#52, frontend-design §5): who the Patient is, at a glance, on every Patient tab.
 * One neutral tint for every Patient (colour carries meaning elsewhere). Specialty Modules add a chip (e.g. the
 * primary cancer); the Open Items button jumps to them.
 */
export function PatientHeader() {
  const { state, careTeam } = usePatient();
  const { modules, showUpcoming } = useViewer();
  const patientId = state.status === "ready" ? state.patient.id : null;
  // The breadcrumb names the Patient, never their id.
  useBreadcrumbLabel(patientId ? `/patients/${patientId}` : "", state.status === "ready" ? state.patient.display_name : null);
  const withOpenItems = isVisible({ stage: 5, built: true }, showUpcoming);
  const [openItems, setOpenItems] = useState<number | null>(null);
  useEffect(() => {
    if (patientId && withOpenItems) fetchPatientOpenItems(patientId).then((items) => setOpenItems(items.length)).catch(() => setOpenItems(null));
  }, [patientId, withOpenItems]);
  const primary = careTeam?.find((member) => member.is_primary && member.is_current);
  const chips = patientHeaderChipsFor(modules);
  return (
    <section aria-label="Patient" className="flex flex-wrap items-center justify-between gap-3 pb-3">
      {state.status === "loading" && <span role="status" className="text-sm text-muted-foreground">Loading Patient…</span>}
      {state.status === "error" && <span role="alert" className="text-sm text-neg">{state.message}</span>}
      {state.status === "ready" && (
        <>
          <div className="flex min-w-0 items-center gap-3">
            <span aria-hidden className="flex h-9 w-9 flex-none items-center justify-center rounded-full border border-neu-bd bg-card text-[13px] font-semibold text-neu">
              {initials(state.patient.display_name)}
            </span>
            <div className="flex min-w-0 flex-col gap-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="m-0 text-lg font-semibold">{state.patient.display_name}</h1>
                <PseudonymChip pseudonym={state.patient.pseudonym} />
                {chips.map((Chip, i) => <Chip key={i} patientId={state.patient.id} />)}
              </div>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                <span>DOB {formatDob(state.patient.identity.dob)}</span>
                <span className="font-mono">MRN {state.patient.identity.mrn ?? "—"}</span>
                {primary && <span title={CARE_TEAM_ROLE_LABEL[primary.role]}>Primary: <span className="text-foreground">{primary.provider_name}</span></span>}
                {suburb(state.patient.identity.address) && (
                  <span className="inline-flex items-center gap-1"><MapPin aria-hidden className="h-3 w-3" />{suburb(state.patient.identity.address)}</span>
                )}
              </div>
            </div>
          </div>
          {openItems !== null && openItems > 0 && (
            <Link href={`/patients/${state.patient.id}/summary#open-items`}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-cau-bd bg-cau-bg px-3 text-[13px] font-medium text-cau">
              <CircleDot aria-hidden className="h-3.5 w-3.5" />{openItems} Open Items
            </Link>
          )}
        </>
      )}
    </section>
  );
}
