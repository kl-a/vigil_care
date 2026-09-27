"use client";

import { useCallback, useEffect, useState } from "react";
import { OpenItemList } from "@/components/openItems/OpenItemList";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { messageOf } from "@/lib/api";
import { fetchOpenItems, mayAct, WHO_LABEL, type OpenItem, type Who } from "@/lib/summary";

const CHIP = "h-7 rounded-full border px-3 text-xs font-medium";
// A selected filter is a state, not an action: neutral, not the primary colour (frontend-design §4.1).
const chip = (on: boolean) => `${CHIP} ${on ? "border-foreground bg-muted text-foreground" : "border-border text-muted-foreground hover:bg-muted"}`;

/**
 * Dashboard (#48, design doc §5 screen 2): the Practice's Open Items queue, filtered by type and by who can act.
 * Only this Practice's; the developer admin's Dashboard is System status instead.
 */
export function Dashboard() {
  const me = useSignedInUser();
  const [items, setItems] = useState<OpenItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [type, setType] = useState<string | null>(null);
  const [who, setWho] = useState<Who | "mine" | null>(null);
  const load = useCallback(() => { fetchOpenItems().then(setItems).catch((reason: unknown) => setError(messageOf(reason))); }, []);
  useEffect(load, [load]);
  const types = [...new Map((items ?? []).map((i) => [i.type, i.type_label])).entries()];
  const shown = (items ?? []).filter((i) => (type === null || i.type === type)
    && (who === null || (who === "mine" ? mayAct(i.who, me.job_title) : i.who === who)));
  return (
    <div data-screen-label="Dashboard" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-col gap-1">
        <h1 className="m-0 text-xl font-semibold">Open Items</h1>
        <p className="m-0 text-[13px] text-muted-foreground">Everything in this Practice that someone needs to act on. Each clears when it&apos;s done; nothing is dismissed.</p>
      </div>
      {items && items.length > 0 && (
        <div className="flex flex-col gap-2">
          <div role="group" aria-label="Filter by type" className="flex flex-wrap gap-2">
            <button onClick={() => setType(null)} aria-pressed={type === null} className={chip(type === null)}>All ({items.length})</button>
            {types.map(([key, label]) => (
              <button key={key} onClick={() => setType(key)} aria-pressed={type === key} className={chip(type === key)}>
                {label} ({items.filter((i) => i.type === key).length})
              </button>
            ))}
          </div>
          <div role="group" aria-label="Filter by who can act" className="flex flex-wrap gap-2">
            <button onClick={() => setWho(null)} aria-pressed={who === null} className={chip(who === null)}>Anyone</button>
            <button onClick={() => setWho("mine")} aria-pressed={who === "mine"} className={chip(who === "mine")}>I can act</button>
            {(["clinician", "staff"] as const).map((w) => (
              <button key={w} onClick={() => setWho(w)} aria-pressed={who === w} className={chip(who === w)}>{WHO_LABEL[w]}</button>
            ))}
          </div>
        </div>
      )}
      <section aria-label="Open Items queue" className="rounded-md border border-border bg-card p-4">
        {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
        {items === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Open Items…</p>}
        {items && <OpenItemList items={shown} showPatient onActed={load} />}
      </section>
    </div>
  );
}
