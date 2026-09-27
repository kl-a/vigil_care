"use client";

import { useCallback, useEffect, useState } from "react";
import { messageOf } from "@/lib/api";
import { fetchPatientOpenItems, type OpenItem } from "@/lib/summary";
import { OpenItemList } from "./OpenItemList";

/** One Patient's Open Items, on the Overview and the Summary. */
export function PatientOpenItems({ patientId, initial }: { patientId: string; initial?: OpenItem[] }) {
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
      {items && <OpenItemList items={items} onActed={load} />}
    </section>
  );
}
