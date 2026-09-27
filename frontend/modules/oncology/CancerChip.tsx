"use client";

import { useEffect, useState } from "react";
import { fetchCancerDiagnoses, type CancerDiagnosisRow } from "./CancerDiagnoses";

/** The Patient header's chip (#52): the active primary cancer(s), e.g. "Colorectal cancer · Stage IIIB (dx)". */
export function CancerChip({ patientId }: { patientId: string }) {
  const [diagnoses, setDiagnoses] = useState<CancerDiagnosisRow[]>([]);
  useEffect(() => { fetchCancerDiagnoses(patientId).then(setDiagnoses).catch(() => setDiagnoses([])); }, [patientId]);
  // Cancers with no evidence of disease stay in the record but not in the header.
  const active = diagnoses.filter((d) => d.cancer_status !== "no_evidence_of_disease");
  return (
    <>
      {(active.length > 0 ? active : diagnoses).slice(0, 2).map((d) => (
        <span key={d.id} className="inline-flex items-center rounded-full border border-border bg-card px-2.5 py-0.5 text-xs font-medium">
          {d.name}{d.stage && ` · Stage ${d.stage} (dx)`}
        </span>
      ))}
    </>
  );
}
