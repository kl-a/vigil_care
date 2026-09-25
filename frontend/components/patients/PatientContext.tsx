"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { messageOf } from "@/lib/api";
import { CARE_TEAM_ROLE_LABEL, fetchCareTeam, type CareTeamRow } from "@/lib/careTeam";
import { fetchPatient, formatDob, type PatientDetail } from "@/lib/patients";

type PatientState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; patient: PatientDetail };

interface PatientContextValue {
  state: PatientState;
  /** After a change: the backend's answer becomes the Patient everyone on the page sees. */
  update: (patient: PatientDetail) => void;
  /** The Care Team (#9), or null while loading or if it couldn't be read. */
  careTeam: CareTeamRow[] | null;
  reloadCareTeam: () => void;
}

const PatientContext = createContext<PatientContextValue | null>(null);

/** One Patient, loaded once for the header and whichever Patient tab is open. */
export function PatientProvider({ patientId, children }: { patientId: string; children: ReactNode }) {
  const [state, setState] = useState<PatientState>({ status: "loading" });
  const load = useCallback(() => {
    setState({ status: "loading" });
    fetchPatient(patientId)
      .then((patient) => setState({ status: "ready", patient }))
      .catch((reason: unknown) => setState({ status: "error", message: messageOf(reason) }));
  }, [patientId]);
  useEffect(load, [load]);
  const update = useCallback((patient: PatientDetail) => setState({ status: "ready", patient }), []);
  const [careTeam, setCareTeam] = useState<CareTeamRow[] | null>(null);
  const reloadCareTeam = useCallback(() => {
    fetchCareTeam(patientId).then(setCareTeam).catch(() => setCareTeam(null));
  }, [patientId]);
  useEffect(reloadCareTeam, [reloadCareTeam]);
  return <PatientContext.Provider value={{ state, update, careTeam, reloadCareTeam }}>{children}</PatientContext.Provider>;
}

export function usePatient(): PatientContextValue {
  const value = useContext(PatientContext);
  if (!value) throw new Error("usePatient needs a PatientProvider");
  return value;
}

/** The Patient header (design doc §5 screen 4): who this is, on every Patient screen. */
export function PatientHeader() {
  const { state, careTeam } = usePatient();
  const primary = careTeam?.find((member) => member.is_primary && member.is_current);
  return (
    <section aria-label="Patient" className="flex flex-wrap items-baseline gap-x-4 gap-y-1 pb-2">
      {state.status === "loading" && <span role="status" className="text-sm text-muted-foreground">Loading Patient…</span>}
      {state.status === "error" && <span role="alert" className="text-sm text-neg">{state.message}</span>}
      {state.status === "ready" && (
        <>
          <h1 className="m-0 text-lg font-semibold">{state.patient.display_name}</h1>
          <span className="text-[13px] text-muted-foreground">DOB {formatDob(state.patient.identity.dob)}</span>
          <span className="font-mono text-xs text-muted-foreground">MRN {state.patient.identity.mrn ?? "—"}</span>
          <span className="font-mono text-xs text-muted-foreground" title="Pseudonym: printed only on De-identified Exports">{state.patient.pseudonym}</span>
          {primary && <span className="text-[13px]">{CARE_TEAM_ROLE_LABEL[primary.role]}: {primary.provider_name}</span>}
        </>
      )}
    </section>
  );
}
