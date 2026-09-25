import { INSTALLED_MODULES } from "@/modules";
import type { ModuleManifest, PatientTab, SectionDefinition, SectionSlotName } from "./types";

export const MODULES: readonly ModuleManifest[] = INSTALLED_MODULES;

const CORE_PATIENT_TABS: readonly PatientTab[] = [
  { segment: "overview", label: "Overview", screen: 4 },
  { segment: "summary", label: "Summary", screen: 15 },
  { segment: "clinical-data", label: "Clinical Data", screen: 9 },
  { segment: "documents", label: "Documents" },
  { segment: "medications", label: "Medications", screen: 10 },
  { segment: "trials", label: "Trials", screen: 13 },
  { segment: "exports", label: "Exports", screen: 16 },
];

/** Until per-Practice activation arrives from the API (ticket #3), it comes from configuration. */
export const ACTIVE_MODULES: readonly string[] = (process.env.NEXT_PUBLIC_VIGIL_ACTIVE_MODULES ?? "oncology")
  .split(",").map((key) => key.trim()).filter(Boolean);

function active(keys: readonly string[]): ModuleManifest[] {
  return MODULES.filter((module) => keys.includes(module.key));
}

export function sectionsFor(slot: SectionSlotName, activeModules: readonly string[]): SectionDefinition[] {
  return active(activeModules)
    .flatMap((module) => module.sections.filter((section) => section.slot === slot))
    .sort((a, b) => a.order - b.order);
}

/** Core tabs, with module tabs inserted before Trials. */
export function patientTabsFor(activeModules: readonly string[]): PatientTab[] {
  const moduleTabs = active(activeModules).flatMap((module) => module.patientTabs);
  const trials = CORE_PATIENT_TABS.findIndex((tab) => tab.segment === "trials");
  return [...CORE_PATIENT_TABS.slice(0, trials), ...moduleTabs, ...CORE_PATIENT_TABS.slice(trials)];
}
