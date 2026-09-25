"use client";

import { sectionsFor } from "@/lib/modules/registry";
import type { ModuleKey, SectionSlotName } from "@/lib/modules/types";
import { useViewer } from "./shell/ViewerProvider";

/** Renders the sections that the Practice's active Specialty Modules register for a slot. */
export function SectionSlot({ slot, activeModules }: { slot: SectionSlotName; activeModules?: readonly ModuleKey[] }) {
  const viewer = useViewer();
  const sections = sectionsFor(slot, activeModules ?? viewer.activeModules);
  if (sections.length === 0) return null;
  return (
    <>
      {sections.map((section) => (
        <section key={section.id} aria-label={section.title} className="rounded-md border border-border bg-card p-4">
          <h2 className="mb-1 text-sm font-semibold">{section.title}</h2>
          {section.render()}
        </section>
      ))}
    </>
  );
}
