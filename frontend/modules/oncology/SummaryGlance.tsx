import { formatDate } from "@/lib/format";
import type { SummaryGlanceExtension } from "@/lib/modules/types";
import { fetchCancerDiagnoses } from "./CancerDiagnoses";
import { fetchPerformanceStatus } from "./Observations";
import { DirectionPill, fetchResponseAssessments } from "./ResponseAssessments";

const EXTENT: Record<string, string> = { localised: "localised", locally_advanced: "locally advanced", metastatic: "metastatic", unknown: "extent unknown" };

/**
 * Oncology's tiles on the Patient Summary's at-a-glance strip (#53): the active primary cancer, the latest
 * Response Assessment that counts, and the latest ECOG.
 */
export const oncologySummaryGlance: SummaryGlanceExtension = {
  load: async (patientId) => {
    const [diagnoses, assessments, ecog] = await Promise.all([
      fetchCancerDiagnoses(patientId).catch(() => []), fetchResponseAssessments(patientId).catch(() => []), fetchPerformanceStatus(patientId).catch(() => []),
    ]);
    const primary = diagnoses.find((d) => d.cancer_status !== "no_evidence_of_disease") ?? diagnoses[0];
    const latest = assessments.find((a) => !a.overridden_by_id);
    return [
      {
        key: "diagnosis", order: 10, label: "Diagnosis", value: primary?.name ?? null,
        detail: primary && [primary.stage && `Stage ${primary.stage} at dx`, `now ${EXTENT[primary.disease_extent] ?? primary.disease_extent}`].filter(Boolean).join(" · "),
      },
      {
        key: "latest-response", order: 30, label: "Latest response", value: latest ? <DirectionPill direction={latest.direction} /> : null,
        detail: latest && `${formatDate(latest.assessed_on)}${latest.cancer_diagnosis_name ? ` · ${latest.cancer_diagnosis_name}` : " · not attributed"}`,
      },
      { key: "ecog", order: 40, label: "ECOG", value: ecog[0] ? `${ecog[0].value}` : null, detail: ecog[0] && formatDate(ecog[0].assessed_on) },
    ];
  },
};
