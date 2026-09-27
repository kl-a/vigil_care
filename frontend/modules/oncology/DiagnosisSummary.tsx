"use client";

import { useEffect, useState } from "react";
import { usePatient } from "@/components/patients/PatientContext";
import { Updated } from "@/components/summary/Updated";
import { request, type Schemas } from "@/lib/api";
import { CancerDiagnosisBlocks } from "./CancerDiagnoses";

export const fetchDiagnosisUpdated = (patientId: string) => request<Schemas["LastUpdated"] | null>(`/patients/${patientId}/diagnosis-updated`);

/** The Patient Summary's Diagnosis section (#47): one block per Cancer Diagnosis, and when it was last updated. */
export function DiagnosisSummary() {
  const { state } = usePatient();
  const patientId = state.status === "ready" ? state.patient.id : null;
  const [updated, setUpdated] = useState<Schemas["LastUpdated"] | null>(null);
  useEffect(() => { if (patientId) fetchDiagnosisUpdated(patientId).then(setUpdated).catch(() => setUpdated(null)); }, [patientId]);
  return (
    <div className="flex flex-col gap-2">
      <p className="m-0 text-xs text-muted-foreground">
        <Updated updated={updated} href={patientId ? `/patients/${patientId}/clinical-data?tab=cancer-diagnosis` : undefined} />
      </p>
      <CancerDiagnosisBlocks stacked />
    </div>
  );
}
