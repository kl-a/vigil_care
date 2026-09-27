"use client";

import { useEffect, useState } from "react";
import { fetchInactiveModuleFacts, type ModuleFacts } from "@/lib/clinical";

/**
 * Facts recorded by a Specialty Module that isn't active at this Practice (ADR 0004, amended): a module owns
 * tools, not visibility, so its facts stay visible, read-only and in plain words. Shows nothing otherwise.
 */
export function InactiveModuleFacts({ patientId }: { patientId: string }) {
  const [modules, setModules] = useState<ModuleFacts[]>([]);
  useEffect(() => {
    fetchInactiveModuleFacts(patientId).then(setModules).catch(() => setModules([]));
  }, [patientId]);
  if (modules.length === 0) return null;
  return (
    <>
      {modules.map((module) => (
        <section key={module.module} aria-label={`${module.display_name} (read-only)`} className="flex flex-col gap-2 rounded-md border border-border bg-card p-4">
          <h2 className="m-0 text-sm font-semibold">{module.display_name} <span className="font-normal text-muted-foreground">(read-only)</span></h2>
          <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-[13px]">
            {module.facts.map((fact) => <li key={fact}>{fact}</li>)}
          </ul>
          <p className="m-0 text-xs text-muted-foreground">
            Recorded while the {module.display_name} module was in use. It isn&apos;t active at this Practice now, so these can&apos;t be changed here, but they stay part of the record.
          </p>
        </section>
      ))}
    </>
  );
}
