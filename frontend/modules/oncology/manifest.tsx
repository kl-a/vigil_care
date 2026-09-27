import type { ModuleManifest } from "@/lib/modules/types";
import { BiomarkersTab } from "./Biomarkers";
import { CancerDiagnosesTab, CancerDiagnosisBlocks, NewPrimaryCancer } from "./CancerDiagnoses";
import { lineOfTherapyExtension } from "./LinesOfTherapy";
import { CnsTab, PerformanceStatusTab } from "./Observations";

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
  builtSections: { "cancer-diagnosis": "4a", biomarkers: "4a", "performance-status": "4c", cns: "4c" },
  conditionExtension: { factKind: "cancer_diagnosis", label: "This is a primary cancer", Form: NewPrimaryCancer },
  treatmentCourseExtension: lineOfTherapyExtension,
  sections: {
    "cancer-diagnoses": () => <CancerDiagnosisBlocks />,
    "cancer-diagnosis": () => <CancerDiagnosesTab />,
    diagnosis: () => <SectionNote text="One block per Cancer Diagnosis: Stage (at diagnosis), Disease Extent (now), Biomarkers, Recurrences." />,
    "response-assessments": () => <SectionNote text="Responding / Stable / Progressing over time." />,
    biomarkers: () => <BiomarkersTab />,
    "performance-status": () => <PerformanceStatusTab />,
    cns: () => <CnsTab />,
  },
};
