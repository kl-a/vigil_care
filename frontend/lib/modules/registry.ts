import { INSTALLED_MODULES } from "@/modules";
import type { ModuleKey, ModuleManifest, PatientTab, SectionDefinition, SectionSlotName } from "./types";

const CORE_PATIENT_TABS: readonly PatientTab[] = [
  { segment: "overview", label: "Overview", slot: "patient-overview", screen: { number: 4, title: "Patient Overview", purpose: "Clinical profile for one Patient." } },
  { segment: "summary", label: "Summary", slot: "patient-summary", screen: { number: 15, title: "Patient Summary", purpose: "The consultation-ready “At a Glance” page." } },
  { segment: "clinical-data", label: "Clinical Data", slot: "clinical-data-tabs", screen: { number: 9, title: "Clinical Data Viewer", purpose: "Longitudinal Clinical Record." } },
  { segment: "documents", label: "Documents", screen: { title: "Patient Documents", purpose: "This Patient's Documents." } },
  { segment: "medications", label: "Medications", screen: { number: 10, title: "Medication Manager", purpose: "Medication list with reconciliation." } },
  { segment: "trials", label: "Trials", screen: { number: 13, title: "Match Board", purpose: "Patient vs trials for a target Condition." } },
  { segment: "exports", label: "Exports", screen: { number: 16, title: "Exports", purpose: "Generate and sign off Identified or De-identified Exports." } },
];

/**
 * Specialty Modules active for this Practice. Until per-Practice activation comes from the API
 * (ticket #3), it is configuration. The Core never assumes any module is active.
 */
export const ACTIVE_MODULES: readonly ModuleKey[] = (process.env.NEXT_PUBLIC_VIGIL_ACTIVE_MODULES ?? "")
  .split(",").map((key) => key.trim()).filter(Boolean);

function active(keys: readonly ModuleKey[]): ModuleManifest[] {
  return INSTALLED_MODULES.filter((module) => keys.includes(module.key));
}

export function sectionsFor(slot: SectionSlotName, activeModules: readonly ModuleKey[]): SectionDefinition[] {
  return active(activeModules)
    .flatMap((module) => module.sections.filter((section) => section.slot === slot))
    .sort((a, b) => a.order - b.order);
}

/** Core tabs, with module tabs inserted before Trials. */
export function patientTabsFor(activeModules: readonly ModuleKey[]): PatientTab[] {
  const moduleTabs = active(activeModules).flatMap((module) => module.patientTabs);
  const trials = CORE_PATIENT_TABS.findIndex((tab) => tab.segment === "trials");
  return [...CORE_PATIENT_TABS.slice(0, trials), ...moduleTabs, ...CORE_PATIENT_TABS.slice(trials)];
}
