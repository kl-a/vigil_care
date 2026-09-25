import { INSTALLED_MODULES } from "@/modules";
import type { ModuleConfiguration, PatientTab, SectionDefinition, SectionSlotName } from "./types";

const CORE_PATIENT_TABS: readonly PatientTab[] = [
  { segment: "overview", label: "Overview", slot: "patient-overview", screen: { number: 4, title: "Patient Overview", purpose: "Clinical profile for one Patient.", stage: 2, built: true } },
  { segment: "summary", label: "Summary", slot: "patient-summary", screen: { number: 15, title: "Patient Summary", purpose: "The consultation-ready “At a Glance” page.", stage: 5 } },
  { segment: "clinical-data", label: "Clinical Data", slot: "clinical-data-tabs", screen: { number: 9, title: "Clinical Data Viewer", purpose: "Longitudinal Clinical Record.", stage: 4 } },
  { segment: "documents", label: "Documents", screen: { title: "Patient Documents", purpose: "This Patient's Documents.", stage: 6 } },
  { segment: "medications", label: "Medications", screen: { number: 10, title: "Medication Manager", purpose: "Medication list with reconciliation.", stage: 4 } },
  { segment: "trials", label: "Trials", screen: { number: 13, title: "Match Board", purpose: "Patient vs trials for a target Condition.", stage: 10 } },
  { segment: "exports", label: "Exports", screen: { number: 16, title: "Exports", purpose: "Generate and sign off Identified or De-identified Exports.", stage: 12 } },
];

function manifest(key: string) {
  return INSTALLED_MODULES.find((module) => module.key === key);
}

/**
 * A slot's sections: which, in what order and with what title comes from the API (the Builder);
 * the renderer from the module's manifest. A section without a renderer here is skipped.
 */
export function sectionsFor(slot: SectionSlotName, config: ModuleConfiguration): SectionDefinition[] {
  return config.sections
    .filter((section) => section.slot === slot)
    .sort((a, b) => a.order - b.order)
    .flatMap((section) => {
      const render = manifest(section.module)?.sections[section.id];
      return render ? [{ id: section.id, slot, title: section.title, order: section.order, render }] : [];
    });
}

/** Core tabs, with the active modules' tabs (from the API) inserted before Trials. */
export function patientTabsFor(config: ModuleConfiguration): PatientTab[] {
  const moduleTabs = config.patient_tabs.flatMap((tab) => {
    const frontend = manifest(tab.module)?.patientTabs[tab.segment];
    return frontend ? [{ segment: tab.segment, label: tab.label, ...frontend }] : [];
  });
  const trials = CORE_PATIENT_TABS.findIndex((tab) => tab.segment === "trials");
  return [...CORE_PATIENT_TABS.slice(0, trials), ...moduleTabs, ...CORE_PATIENT_TABS.slice(trials)];
}
