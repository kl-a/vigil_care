import type { ReactNode } from "react";

/** Places in Core screens where Specialty Modules contribute UI (design doc §4.1). */
export type SectionSlotName = "patient-overview" | "patient-summary" | "clinical-data-tabs";

/** A Specialty Module's key, e.g. "oncology". */
export type ModuleKey = string;

export interface SectionDefinition {
  id: string;
  slot: SectionSlotName;
  title: string;
  order: number;
  render: () => ReactNode;
}

/** What a screen is, for its placeholder and the screen inventory (design doc §5). */
export interface ScreenInfo {
  number?: number;
  title: string;
  purpose: string;
  /** The build stage that ships this screen (design doc §15). */
  stage: number;
  /** True once the screen is real, not a placeholder. Only built screens of shipped stages are shown. */
  built?: boolean;
}

export interface PatientTab {
  segment: string;
  label: string;
  screen: ScreenInfo;
  /** The slot this tab's screen exposes to Specialty Modules, if any. */
  slot?: SectionSlotName;
}

export interface ModuleManifest {
  key: ModuleKey;
  sections: SectionDefinition[];
  patientTabs: PatientTab[];
}
