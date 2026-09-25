import { notFound } from "next/navigation";
import { ScreenPlaceholder } from "@/components/ScreenPlaceholder";
import { SectionSlot } from "@/components/SectionSlot";
import { ACTIVE_MODULES, patientTabsFor } from "@/lib/modules/registry";
import type { SectionSlotName } from "@/lib/modules/types";

/** Core screens expose slots; active Specialty Modules fill them (design doc §4.1). */
const SLOT_FOR_TAB: Partial<Record<string, SectionSlotName>> = {
  overview: "patient-overview",
  summary: "patient-summary",
  "clinical-data": "clinical-data-tabs",
};

export default function PatientTabPage({ params }: { params: { tab: string } }) {
  if (!patientTabsFor(ACTIVE_MODULES).some((tab) => tab.segment === params.tab)) notFound();
  const slot = SLOT_FOR_TAB[params.tab];
  return (
    <ScreenPlaceholder path={`/patients/[id]/${params.tab}`}>
      {slot && <SectionSlot slot={slot} />}
    </ScreenPlaceholder>
  );
}
