"use client";

import { useState } from "react";
import { usePatient } from "@/components/patients/PatientContext";
import { useViewer } from "@/components/shell/ViewerProvider";
import { clinicalDataTabsFor } from "@/lib/modules/registry";
import { Conditions } from "./Conditions";
import { InactiveModuleFacts } from "./InactiveModuleFacts";
import { Labs } from "./Labs";
import { PlanAndNotes } from "./PlanAndNotes";

/** The Clinical Data tab's Core sub-tabs (design doc §5 screen 9); each appears once built (Stage 4a–4c). */
const CORE_SUBTABS = [
  { key: "conditions", label: "Conditions", built: true },
  { key: "labs", label: "Labs", built: true },
  { key: "imaging", label: "Imaging & Findings", built: false },
  { key: "treatment", label: "Treatment Courses", built: false },
  { key: "plan", label: "Plan & notes", built: true },
] as const;

/** Clinical Data Viewer (design doc §5 screen 9): where the Clinical Record is viewed and entered by hand. */
export function ClinicalData() {
  const { state } = usePatient();
  const { modules } = useViewer();
  // Core sub-tabs, then the active modules' built ones.
  const moduleTabs = clinicalDataTabsFor(modules);
  const shown = [...CORE_SUBTABS.filter((tab) => tab.built), ...moduleTabs.map((tab) => ({ key: tab.id, label: tab.title }))];
  const [current, setCurrent] = useState<string>(shown[0]!.key);
  if (state.status !== "ready") return null;
  const patientId = state.patient.id;
  return (
    <div data-screen-label="Clinical Data Viewer" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <nav aria-label="Clinical Data" className="flex gap-1 border-b border-border">
        {shown.map((tab) => (
          <button key={tab.key} onClick={() => setCurrent(tab.key)} aria-current={current === tab.key ? "page" : undefined}
            className={`-mb-px border-b-2 px-3 py-1.5 text-[13px] ${current === tab.key ? "border-primary font-medium text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {tab.label}
          </button>
        ))}
      </nav>
      {current === "conditions" && <Conditions patientId={patientId} />}
      {current === "labs" && <Labs patientId={patientId} />}
      {current === "plan" && <PlanAndNotes patientId={patientId} />}
      {moduleTabs.filter((tab) => tab.id === current).map((tab) => (
        <section key={tab.id} aria-label={tab.title} className="rounded-md border border-border bg-card p-4">{tab.render()}</section>
      ))}
      <InactiveModuleFacts patientId={patientId} />
    </div>
  );
}
