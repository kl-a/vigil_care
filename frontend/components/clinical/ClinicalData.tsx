"use client";

import { useEffect, useState } from "react";
import { usePatient } from "@/components/patients/PatientContext";
import { useViewer } from "@/components/shell/ViewerProvider";
import { SubTabs } from "@/components/ui/SubTabs";
import { fetchClinicalCounts } from "@/lib/clinical";
import { clinicalDataCountsFor, clinicalDataTabsFor } from "@/lib/modules/registry";
import { isPartShipped } from "@/lib/stages";
import { Conditions } from "./Conditions";
import { Imaging } from "./Imaging";
import { InactiveModuleFacts } from "./InactiveModuleFacts";
import { Labs } from "./Labs";
import { PlanAndNotes } from "./PlanAndNotes";
import { TreatmentCourses } from "./TreatmentCourses";

/** The Clinical Data tab's Core sub-tabs (design doc §5 screen 9); each appears once built and its part of
 * Stage 4 has shipped. */
const CORE_SUBTABS = [
  { key: "conditions", label: "Conditions", built: true, part: "4a" },
  { key: "labs", label: "Labs", built: true, part: "4c" },
  { key: "imaging", label: "Imaging & Findings", built: true, part: "4c" },
  { key: "treatment", label: "Treatment Courses", built: true, part: "4b" },
  { key: "plan", label: "Plan & notes", built: true, part: "4c" },
] as const;

/** Clinical Data Viewer (design doc §5 screen 9): where the Clinical Record is viewed and entered by hand. */
export function ClinicalData() {
  const { state } = usePatient();
  const { modules, showUpcoming } = useViewer();
  // Core sub-tabs, then the active modules' built ones; each once its part has shipped.
  const moduleTabs = clinicalDataTabsFor(modules).filter((tab) => isPartShipped(tab.part, showUpcoming));
  // Each sub-tab's count (#57): the Core's, and each active module's for its own.
  const [counts, setCounts] = useState<Record<string, number>>({});
  const patientReady = state.status === "ready" ? state.patient.id : null;
  useEffect(() => {
    if (!patientReady) return;
    const loaders = [fetchClinicalCounts, ...clinicalDataCountsFor(modules)];
    Promise.all(loaders.map((load) => load(patientReady).catch(() => ({})))).then((all) => setCounts(Object.assign({}, ...all)));
  }, [patientReady, modules]);
  const shown = [
    ...CORE_SUBTABS.filter((tab) => tab.built && isPartShipped(tab.part, showUpcoming)),
    ...moduleTabs.map((tab) => ({ key: tab.id, label: tab.title })),
  ].map((tab) => ({ ...tab, count: counts[tab.key] ?? null }));
  // A link may open a sub-tab, e.g. the Patient Summary's "See it in the record" (?tab=labs). A Specialty
  // Module's sub-tabs arrive once the Practice's modules have loaded, so the asked-for tab is kept until then.
  const [asked, setAsked] = useState(() => (typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("tab")));
  const [chosen, setChosen] = useState<string | null>(null);
  const current = chosen ?? shown.find((tab) => tab.key === asked)?.key ?? shown[0]!.key;
  const setCurrent = (key: string) => { setChosen(key); setAsked(null); };
  if (state.status !== "ready") return null;
  const patientId = state.patient.id;
  return (
    <div data-screen-label="Clinical Data Viewer" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <SubTabs label="Clinical Data" tabs={shown} current={current} onChange={setCurrent} />
      {current === "conditions" && <Conditions patientId={patientId} />}
      {current === "labs" && <Labs patientId={patientId} />}
      {current === "imaging" && <Imaging patientId={patientId} />}
      {current === "plan" && <PlanAndNotes patientId={patientId} />}
      {current === "treatment" && <TreatmentCourses patientId={patientId} />}
      {moduleTabs.filter((tab) => tab.id === current).map((tab) => (
        <section key={tab.id} aria-label={tab.title} className="rounded-md border border-border bg-card p-4">{tab.render()}</section>
      ))}
      <InactiveModuleFacts patientId={patientId} />
    </div>
  );
}
