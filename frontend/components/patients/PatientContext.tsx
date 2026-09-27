"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { messageOf } from "@/lib/api";
import { fetchCareTeam, type CareTeamRow } from "@/lib/careTeam";
import { fetchPatient, type PatientDetail } from "@/lib/patients";

type PatientState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; patient: PatientDetail };

interface PatientContextValue {
  state: PatientState;
  /** After a change: the backend's answer becomes the Patient everyone on the page sees. */
  update: (patient: PatientDetail) => void;
  /** The Care Team (#9), or null while loading. */
  careTeam: CareTeamRow[] | null;
  careTeamError: string | null;
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
  const [careTeamError, setCareTeamError] = useState<string | null>(null);
  const reloadCareTeam = useCallback(() => {
    fetchCareTeam(patientId)
      .then((team) => { setCareTeam(team); setCareTeamError(null); })
      .catch((reason: unknown) => setCareTeamError(messageOf(reason)));
  }, [patientId]);
  useEffect(reloadCareTeam, [reloadCareTeam]);
  return (
    <PatientContext.Provider value={{ state, update, careTeam, careTeamError, reloadCareTeam }}>{children}</PatientContext.Provider>
  );
}

export function usePatient(): PatientContextValue {
  const value = useContext(PatientContext);
  if (!value) throw new Error("usePatient needs a PatientProvider");
  return value;
}

/** The Patient header (design doc §5 screen 4): who this is, on every Patient screen. */
