import type { ReactNode } from "react";

/** Places in Core screens where Specialty Modules contribute UI (design doc §4.1). */
export type SectionSlotName = "patient-overview" | "patient-summary" | "clinical-data-tabs";

export interface SectionDefinition {
  id: string;
  slot: SectionSlotName;
  title: string;
  order: number;
  render: () => ReactNode;
}

export interface PatientTab {
  segment: string;
  label: string;
  /** Screen number from design doc §5, when the tab is a numbered screen. */
  screen?: number;
}

export interface ModuleManifest {
  key: string;
  displayName: string;
  sections: SectionDefinition[];
  patientTabs: PatientTab[];
}
