"use client";

import { sectionsFor } from "@/lib/modules/registry";
import type { SectionSlotName } from "@/lib/modules/types";
import { useViewer } from "./shell/ViewerProvider";
import { SectionCard } from "./ui/SectionCard";

/** Renders the sections that the Practice's active Specialty Modules register for a slot, each in a SectionCard. */
export function SectionSlot({ slot }: { slot: SectionSlotName }) {
  const { modules } = useViewer();
  const sections = sectionsFor(slot, modules);
  if (sections.length === 0) return null;
  return (
    <>
      {sections.map((section) => (
        <SectionCard key={section.id} id={`section-${section.id}`} title={section.title}>{section.render()}</SectionCard>
      ))}
    </>
  );
}
