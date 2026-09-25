import type { ModuleManifest } from "@/lib/modules/types";

function SectionNote({ text }: { text: string }) {
  return <p className="text-sm text-muted-foreground">{text}</p>;
}

/** Oncology: the first Specialty Module. All oncology UI registers here, never in Core screens. */
export const oncologyManifest: ModuleManifest = {
  key: "oncology",
  patientTabs: [{
    segment: "treatment-options",
    label: "Treatment Options",
    screen: { number: 11, title: "Treatment Options", purpose: "Standard-of-care options for one Cancer Diagnosis (eviQ + PBS)." },
  }],
  sections: [
    { id: "cancer-diagnoses", slot: "patient-overview", title: "Cancer Diagnoses", order: 10,
      render: () => <SectionNote text="Cancer Type, Stage, Disease Extent and Biomarkers per Cancer Diagnosis." /> },
    { id: "diagnosis", slot: "patient-summary", title: "Diagnosis", order: 20,
      render: () => <SectionNote text="One block per Cancer Diagnosis: Stage (at diagnosis), Disease Extent (now), Biomarkers, Recurrences." /> },
    { id: "response-assessments", slot: "clinical-data-tabs", title: "Response Assessments", order: 10, render: () => <SectionNote text="Responding / Stable / Progressing over time." /> },
    { id: "biomarkers", slot: "clinical-data-tabs", title: "Biomarkers", order: 20, render: () => <SectionNote text="Full Biomarker history by specimen and date." /> },
    { id: "performance-status", slot: "clinical-data-tabs", title: "Performance Status", order: 30, render: () => <SectionNote text="ECOG over time." /> },
    { id: "cns", slot: "clinical-data-tabs", title: "CNS", order: 40, render: () => <SectionNote text="CNS status." /> },
  ],
};
