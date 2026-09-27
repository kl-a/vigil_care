import { formatDate } from "@/lib/format";
import type { SummaryGlanceExtension } from "@/lib/modules/types";
import { activePrimaries, DISEASE_EXTENT_LABEL, fetchCancerDiagnoses } from "./CancerDiagnoses";
import { fetchPerformanceStatus } from "./Observations";
import { DirectionPill, fetchResponseAssessments } from "./ResponseAssessments";


/**
 * Oncology's tiles on the Patient Summary's at-a-glance strip (#53): the active primary cancer, the latest
 * Response Assessment that counts, and the latest ECOG.
 */
export const oncologySummaryGlance: SummaryGlanceExtension = {
  load: async (patientId) => {
    const [diagnoses, assessments, ecog] = await Promise.all([
      fetchCancerDiagnoses(patientId).catch(() => []), fetchResponseAssessments(patientId).catch(() => []), fetchPerformanceStatus(patientId).catch(() => []),
    ]);
    const primary = activePrimaries(diagnoses)[0];
    const latest = assessments.find((a) => !a.overridden_by_id);
    return [
      {
        key: "diagnosis", order: 10, label: "Diagnosis", value: primary?.name ?? null,
        detail: primary && [primary.stage && `Stage ${primary.stage} at dx`, primary.disease_extent === "unknown" ? "Disease Extent unknown" : `now ${DISEASE_EXTENT_LABEL[primary.disease_extent].toLowerCase()}`].filter(Boolean).join(" · "),
      },
      {
        key: "latest-response", order: 30, label: "Latest Response Assessment", value: latest ? <DirectionPill direction={latest.direction} /> : null,
        detail: latest && `${formatDate(latest.assessed_on)}${latest.cancer_diagnosis_name ? ` · ${latest.cancer_diagnosis_name}` : " · not attributed"}`,
      },
      { key: "ecog", order: 40, label: "ECOG", value: ecog[0] ? `${ecog[0].value}` : null, detail: ecog[0] && formatDate(ecog[0].assessed_on) },
    ];
  },
};
