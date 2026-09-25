import { ACTIVE_MODULES, sectionsFor } from "@/lib/modules/registry";
import type { SectionSlotName } from "@/lib/modules/types";

/** Renders the sections that active Specialty Modules register for a slot. */
export function SectionSlot({ slot, activeModules = ACTIVE_MODULES }: { slot: SectionSlotName; activeModules?: readonly string[] }) {
  const sections = sectionsFor(slot, activeModules);
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
