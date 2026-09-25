"use client";

import { notFound } from "next/navigation";
import { ScreenPlaceholder } from "@/components/ScreenPlaceholder";
import { SectionSlot } from "@/components/SectionSlot";
import { useViewer } from "@/components/shell/ViewerProvider";
import { patientTabsFor } from "@/lib/modules/registry";

/** Core and module Patient tabs share this route; a tab's slot is filled by the Practice's active modules. */
export default function PatientTabPage({ params }: { params: { tab: string } }) {
  const { modules, modulesReady } = useViewer();
  const tab = patientTabsFor(modules).find((candidate) => candidate.segment === params.tab);
  if (!tab && !modulesReady) return <p role="status" className="p-5 text-sm text-muted-foreground">Loading…</p>;
  if (!tab) notFound();
  return (
    <ScreenPlaceholder path={`/patients/[id]/${tab.segment}`}>
      {tab.slot && <SectionSlot slot={tab.slot} />}
    </ScreenPlaceholder>
  );
}
