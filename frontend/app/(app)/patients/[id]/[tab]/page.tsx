import { notFound } from "next/navigation";
import { ScreenPlaceholder } from "@/components/ScreenPlaceholder";
import { SectionSlot } from "@/components/SectionSlot";
import { ACTIVE_MODULES, patientTabsFor } from "@/lib/modules/registry";

/** Core and module Patient tabs share this route; a tab's slot is filled by active Specialty Modules. */
export default function PatientTabPage({ params }: { params: { tab: string } }) {
  const tab = patientTabsFor(ACTIVE_MODULES).find((candidate) => candidate.segment === params.tab);
  if (!tab) notFound();
  return (
    <ScreenPlaceholder path={`/patients/[id]/${tab.segment}`}>
      {tab.slot && <SectionSlot slot={tab.slot} />}
    </ScreenPlaceholder>
  );
}
