import type { ReactNode } from "react";

/** Places in Core screens where Specialty Modules contribute UI (design doc §4.1). */
export type SectionSlotName = "patient-overview" | "patient-summary" | "clinical-data-tabs";

/** A Specialty Module's key, e.g. "oncology". */
export type ModuleKey = string;

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

/**
 * The Practice's active modules, their sections and Patient tabs: the Builder's output from
 * GET /modules/active (#15). The backend decides *what* appears; the frontend supplies *how* it renders.
 */
export interface ModuleConfiguration {
  active_modules: ModuleKey[];
  sections: { module: ModuleKey; id: string; slot: string; title: string; order: number }[];
  patient_tabs: { module: ModuleKey; segment: string; label: string }[];
}

export const NO_MODULES: ModuleConfiguration = { active_modules: [], sections: [], patient_tabs: [] };

/** A rendered section: the API's section plus the module's renderer. */
export interface SectionDefinition {
  id: string;
  slot: SectionSlotName;
  title: string;
  order: number;
  render: () => ReactNode;
}

/** A module's frontend: renderers for the sections and screens its backend declares. */
export interface ModuleManifest {
  key: ModuleKey;
  sections: Record<string, () => ReactNode>;
  patientTabs: Record<string, { screen: ScreenInfo; slot?: SectionSlotName }>;
}
