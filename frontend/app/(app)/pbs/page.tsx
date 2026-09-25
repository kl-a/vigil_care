"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PbsScheduleNote } from "@/components/pbs/PbsScheduleNote";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import { searchPbs, type PbsDrugRow } from "@/lib/pbs";

const TYPING_PAUSE_MS = 200;

/** PBS Drug Lookup (design doc §5 screen 14, #20): search the current PBS Schedule, results as you type. */
export default function PbsPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<PbsDrugRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!q.trim()) {
      setResults(null);
      return;
    }
    let current = true;
    const timer = setTimeout(() => {
      searchPbs(q)
        .then((rows) => { if (current) { setResults(rows); setError(null); } })
        .catch((reason: unknown) => { if (current) setError(messageOf(reason)); });
    }, TYPING_PAUSE_MS);
    return () => { current = false; clearTimeout(timer); };
  }, [q]);

  return (
    <div data-screen-label="PBS Drug Lookup" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <h1 className="m-0 text-xl font-semibold">PBS Drug Lookup</h1>
      <PbsScheduleNote />
      <label className="flex flex-col gap-1 text-xs font-medium">
        Drug, brand or active ingredient
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. pembrolizumab, Keytruda or 12120X" autoFocus className={`${FIELD} max-w-md`} />
      </label>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {results && results.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">No oncology drugs in the PBS Schedule match.</p>}
      {results && results.length > 0 && (
        <ul aria-label="Drugs" className="m-0 flex list-none flex-col divide-y divide-border rounded-md border border-border bg-card p-0">
          {results.map((drug) => (
            <li key={drug.drug_name} className="px-3 py-2">
              <span className="flex flex-col">
                <Link href={`/pbs/${drug.item_code}`} className="text-[13px] font-medium text-foreground">{drug.drug_name}</Link>
                <span className="text-xs text-muted-foreground">
                  {drug.brand_names.join(", ") || "No brand name"} · {drug.item_count} PBS {drug.item_count === 1 ? "item" : "items"}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
