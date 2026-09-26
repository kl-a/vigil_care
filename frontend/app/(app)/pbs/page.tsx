"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { PbsListingBadge } from "@/components/pbs/PbsListingBadge";
import { PbsScheduleNote } from "@/components/pbs/PbsScheduleNote";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import {
  drugHref, fetchPbsFilters, LEVELS, listPbsDrugs, listQueryOf, NO_FILTERS, searchParamsOf,
  type PbsDrugPage, type PbsDrugRow, type PbsFilters, type PbsListQuery,
} from "@/lib/pbs";

const TYPING_PAUSE_MS = 250;
const FORMS_SHOWN = 2;

/**
 * PBS Drug Lookup (design doc §5 screen 14, #20, #30): every drug in the current PBS Schedule, A–Z, narrowed by
 * search and filters. The search, filters and page live in the page address, so going back returns to this list.
 */
export default function PbsPage() {
  return (
    <Suspense>
      <PbsDrugList />
    </Suspense>
  );
}

function PbsDrugList() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const query = listQueryOf(new URLSearchParams(params.toString()));
  const queryKey = searchParamsOf(query).toString();

  // The search box updates the address after a pause in typing; the address is the source of truth.
  const [typed, setTyped] = useState(query.q);
  const [filters, setFilters] = useState<PbsFilters | null>(null);
  const [page, setPage] = useState<PbsDrugPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const go = (next: Partial<PbsListQuery>) => {
    // Any change but paging starts again from page 1.
    const changed = searchParamsOf({ ...query, page: 1, ...next }).toString();
    router.replace(changed ? `${pathname}?${changed}` : pathname, { scroll: false });
  };

  useEffect(() => {
    fetchPbsFilters().then(setFilters).catch((reason: unknown) => setError(messageOf(reason)));
  }, []);

  useEffect(() => {
    if (typed.trim() === query.q.trim()) return;
    const timer = setTimeout(() => go({ q: typed }), TYPING_PAUSE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only typing starts a search
  }, [typed]);

  useEffect(() => {
    let current = true;
    listPbsDrugs(listQueryOf(new URLSearchParams(queryKey)))
      .then((result) => { if (current) { setPage(result); setError(null); } })
      .catch((reason: unknown) => { if (current) setError(messageOf(reason)); });
    return () => { current = false; };
  }, [queryKey]);

  const filtered = Boolean(query.q || query.group || query.program || query.level);
  const pages = page ? Math.max(1, Math.ceil(page.total / page.page_size)) : 1;

  return (
    <div data-screen-label="PBS Drug Lookup" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <h1 className="m-0 text-xl font-semibold">PBS Drug Lookup</h1>
      <PbsScheduleNote />
      <div role="search" aria-label="Filter drugs" className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Drug, brand or item code
          <input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="e.g. dexamfetamine, Keytruda or 12120X" className={`${FIELD} w-64`} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Therapeutic group
          <select value={query.group} onChange={(e) => go({ group: e.target.value })} className={`${FIELD} w-60`}>
            <option value="">All groups</option>
            {filters?.groups.map((group) => <option key={group.code} value={group.code}>{group.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          PBS program
          <select value={query.program} onChange={(e) => go({ program: e.target.value })} className={`${FIELD} w-60`}>
            <option value="">All programs</option>
            {filters?.programs.map((program) => <option key={program.code} value={program.code}>{program.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Listing type
          <select value={query.level} onChange={(e) => go({ level: e.target.value })} className={`${FIELD} w-56`}>
            <option value="">Any listing type</option>
            {LEVELS.map((level) => <option key={level.code} value={level.code}>{level.label}</option>)}
          </select>
        </label>
        {filtered && (
          <button onClick={() => { setTyped(""); go(NO_FILTERS); }} className="h-8 px-2 text-xs font-medium text-primary">Clear filters</button>
        )}
      </div>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {!page && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading drugs…</p>}
      {page && (
        <p role="status" className="m-0 text-[13px] text-muted-foreground">
          {page.total === 0 ? "No drugs in the PBS Schedule match." : `${page.total.toLocaleString("en-AU")} ${page.total === 1 ? "drug" : "drugs"}${pages > 1 ? ` · page ${page.page} of ${pages}` : ""}`}
        </p>
      )}
      {page && page.drugs.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table aria-label="Drugs" className="w-full border-collapse text-[13px]">
            <thead className="bg-muted text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Drug (active ingredient) and brands</th>
                <th className="px-3 py-2 font-medium">Forms and strengths</th>
                <th className="px-3 py-2 font-medium">Therapeutic group</th>
                <th className="px-3 py-2 font-medium">Listing types</th>
              </tr>
            </thead>
            <tbody>
              {page.drugs.map((drug) => <DrugRow key={drug.drug_name} drug={drug} from={query} />)}
            </tbody>
          </table>
        </div>
      )}
      {page && pages > 1 && (
        <nav aria-label="Pages" className="flex items-center gap-3 text-[13px]">
          <button disabled={page.page <= 1} onClick={() => go({ page: page.page - 1 })} className="font-medium text-primary disabled:text-muted-foreground">← Previous</button>
          <span className="text-muted-foreground">Page {page.page} of {pages}</span>
          <button disabled={page.page >= pages} onClick={() => go({ page: page.page + 1 })} className="font-medium text-primary disabled:text-muted-foreground">Next →</button>
        </nav>
      )}
    </div>
  );
}

function DrugRow({ drug, from }: { drug: PbsDrugRow; from: PbsListQuery }) {
  const more = drug.forms.length - FORMS_SHOWN;
  return (
    <tr className="border-t border-border align-top">
      <td className="px-3 py-2">
        <Link href={drugHref(drug.item_code, from)} className="font-medium text-foreground">{drug.drug_name}</Link>
        <div className="text-xs text-muted-foreground">{drug.brand_names.join(", ") || "No brand name"}</div>
      </td>
      <td className="px-3 py-2">
        <ul className="m-0 flex list-none flex-col p-0">
          {drug.forms.slice(0, FORMS_SHOWN).map((form) => <li key={form}>{form}</li>)}
        </ul>
        <div className="text-xs text-muted-foreground">
          {more > 0 && `and ${more} more · `}{drug.item_count} PBS {drug.item_count === 1 ? "Item" : "Items"}
        </div>
      </td>
      <td className="px-3 py-2">{drug.groups.map((group) => group.label).join(", ") || <span className="text-muted-foreground">Not classified</span>}</td>
      <td className="px-3 py-2">
        <span className="flex flex-wrap gap-1">{drug.levels.map((level) => <PbsListingBadge key={level} level={level} />)}</span>
      </td>
    </tr>
  );
}
