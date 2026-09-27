"use client";

import { useCallback, useEffect, useState } from "react";
import { messageOf } from "@/lib/api";
import { fetchPatientOpenItems, type OpenItem } from "@/lib/summary";
import { OpenItemCards, OpenItemList } from "./OpenItemList";

/** One Patient's Open Items: a compact list on the Overview, cards on the Summary. */
export function PatientOpenItems({ patientId, initial, cards = false }: { patientId: string; initial?: OpenItem[]; cards?: boolean }) {
  const [items, setItems] = useState<OpenItem[] | null>(initial ?? null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    fetchPatientOpenItems(patientId).then(setItems).catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId]);
  useEffect(() => { if (!initial) load(); }, [load, initial]);
  return (
    <section aria-labelledby="open-items" className="flex flex-col gap-2 rounded-md border border-border bg-card p-4">
      <h2 id="open-items" className="m-0 text-sm font-semibold">Open Items{items && items.length > 0 && ` (${items.length})`}</h2>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {items === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading Open Items…</p>}
      {items && (cards ? <OpenItemCards items={items} onActed={load} /> : <OpenItemList items={items} onActed={load} />)}
    </section>
  );
}
