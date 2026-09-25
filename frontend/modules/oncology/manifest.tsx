import type { ModuleManifest } from "@/lib/modules/types";

function SectionNote({ text }: { text: string }) {
  return <p className="text-sm text-muted-foreground">{text}</p>;
}

/**
 * Oncology's frontend: renderers for the sections and tabs its backend module declares
 * (backend/app/specialties/oncology/module.py). All oncology UI lives here, never in Core screens.
 */
export const oncologyManifest: ModuleManifest = {
  key: "oncology",
  patientTabs: {
    "treatment-options": {
      screen: { number: 11, title: "Treatment Options", purpose: "Standard-of-care options for one Cancer Diagnosis (eviQ + PBS).", stage: 11 },
    },
  },
  sections: {
    "cancer-diagnoses": () => <SectionNote text="Cancer Type, Stage, Disease Extent and Biomarkers per Cancer Diagnosis." />,
    diagnosis: () => <SectionNote text="One block per Cancer Diagnosis: Stage (at diagnosis), Disease Extent (now), Biomarkers, Recurrences." />,
    "response-assessments": () => <SectionNote text="Responding / Stable / Progressing over time." />,
    biomarkers: () => <SectionNote text="Full Biomarker history by specimen and date." />,
    "performance-status": () => <SectionNote text="ECOG over time." />,
    cns: () => <SectionNote text="CNS status." />,
  },
};
