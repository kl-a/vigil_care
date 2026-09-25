"use client";

import { useCallback, useEffect, useState } from "react";
import { SignOffDialog } from "@/components/dialogs/SignOffDialog";
import { useViewer } from "@/components/shell/ViewerProvider";
import { FIELD } from "@/components/ui/styles";
import { StatusPill } from "@/components/ui/StatusPill";
import { messageOf } from "@/lib/api";
import { listModules, setModuleActive, type ModuleStatus } from "@/lib/modules/api";

/** Settings → Specialty Modules (design doc §4.1): developer admins switch them per Practice; data is kept. */
export function SpecialtyModules({ canSwitch, actor }: { canSwitch: boolean; actor: string }) {
  const { refreshModules } = useViewer();
  const [modules, setModules] = useState<ModuleStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [switching, setSwitching] = useState<ModuleStatus | null>(null);
  const [reason, setReason] = useState("");

  const load = useCallback(() => {
    listModules().then(setModules).catch((cause: unknown) => setError(messageOf(cause)));
  }, []);
  useEffect(load, [load]);

  async function confirm(module: ModuleStatus) {
    await setModuleActive(module.key, { is_active: !module.is_active, reason: reason.trim() || undefined });
    setSwitching(null);
    setReason("");
    load();
    await refreshModules(); // its sections and tabs appear or disappear straight away
  }

  return (
    <section aria-labelledby="specialty-modules" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <h2 id="specialty-modules" className="m-0 text-sm font-semibold">Specialty Modules</h2>
      <p className="m-0 max-w-[70ch] text-[13px] text-muted-foreground">
        Each module adds one specialty to Vigil. Switching one off hides its screens and sections for everyone in the Practice; nothing it recorded is deleted, and switching it back on brings everything back.
      </p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {modules === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {modules && (
        <ul aria-label="Specialty Modules" className="m-0 flex list-none flex-col gap-2 p-0">
          {modules.map((module) => (
            <li key={module.key} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border px-3 py-2">
              <span className="flex items-center gap-3">
                <span className="text-[13px] font-medium">{module.display_name}</span>
                <span className="font-mono text-[11px] text-muted-foreground">v{module.version}</span>
                <StatusPill tone={module.is_active ? "pos" : "neu"}>{module.is_active ? "On" : "Off"}</StatusPill>
              </span>
              {canSwitch && (
                <button onClick={() => setSwitching(module)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">
                  {module.is_active ? `Switch ${module.display_name} off` : `Switch ${module.display_name} on`}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {!canSwitch && <p className="m-0 text-xs text-muted-foreground">Only a developer admin switches modules on or off.</p>}
      {switching && (
        <SignOffDialog
          title={`Switch ${switching.display_name} ${switching.is_active ? "off" : "on"}`}
          actor={actor}
          confirmLabel={switching.is_active ? "Switch off" : "Switch on"}
          onConfirm={() => confirm(switching)}
          onClose={() => { setSwitching(null); setReason(""); }}
        >
          <p className="m-0 text-[13px] text-muted-foreground">
            {switching.is_active
              ? `${switching.display_name}'s screens and sections disappear for everyone at this Practice. Its data is kept.`
              : `${switching.display_name}'s screens and sections appear for everyone at this Practice.`}
          </p>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Reason (optional)
            <input id="module-switch-reason" value={reason} onChange={(e) => setReason(e.target.value)} className={FIELD} />
          </label>
        </SignOffDialog>
      )}
    </section>
  );
}
