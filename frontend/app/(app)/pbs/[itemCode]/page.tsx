"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PbsListingBadge } from "@/components/pbs/PbsListingBadge";
import { PbsScheduleNote } from "@/components/pbs/PbsScheduleNote";
import { messageOf } from "@/lib/api";
import { fetchPbsDrug, formatMoney, maximumOf, PROGRAM_LABEL, type PbsDrug, type PbsItemView } from "@/lib/pbs";

/** A drug in the PBS Drug Lookup (design doc §5 screen 14, #20): each PBS item with its Listing per indication. */
export default function PbsDrugPage({ params }: { params: { itemCode: string } }) {
  const [drug, setDrug] = useState<PbsDrug | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPbsDrug(params.itemCode).then(setDrug).catch((reason: unknown) => setError(messageOf(reason)));
  }, [params.itemCode]);

  return (
    <div data-screen-label="PBS Drug Lookup" className="flex w-full max-w-[1200px] flex-col gap-4 px-5 pb-8 pt-3">
      <Link href="/pbs" className="text-xs text-primary">← Search the PBS Schedule</Link>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {!drug && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {drug && (
        <>
          <div className="flex flex-col gap-0.5">
            <h1 className="m-0 text-xl font-semibold">{drug.drug_name}</h1>
            <span className="text-[13px] text-muted-foreground">{drug.brand_names.join(", ") || "No brand name"}</span>
          </div>
          <PbsScheduleNote safetyNet />
          {drug.items.map((item) => <PbsItemCard key={item.item_code} item={item} />)}
        </>
      )}
    </div>
  );
}

function PbsItemCard({ item }: { item: PbsItemView }) {
  const program = item.program_code ? PROGRAM_LABEL[item.program_code] ?? item.program_code : null;
  return (
    <section aria-label={`PBS item ${item.item_code}`} className="flex flex-col gap-2 rounded-md border border-border bg-card p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-sm font-semibold">{item.item_code}</span>
        <span className="text-[13px]">{item.form ?? "—"}</span>
        {program && <span className="text-xs text-muted-foreground">{program}</span>}
      </div>
      <dl className="m-0 flex flex-wrap gap-x-6 gap-y-1 text-[13px] tabular-nums">
        <div className="flex gap-1.5"><dt className="text-muted-foreground">Maximum</dt><dd className="m-0">{maximumOf(item)}</dd></div>
        <div className="flex gap-1.5"><dt className="text-muted-foreground">Repeats</dt><dd className="m-0">{item.repeats ?? "—"} repeats</dd></div>
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">Co-payment</dt>
          <dd className="m-0">{formatMoney(item.copay_general)} general, {formatMoney(item.copay_concessional)} concessional</dd>
        </div>
        {item.brand_names.length > 0 && (
          <div className="flex gap-1.5"><dt className="text-muted-foreground">Brands</dt><dd className="m-0">{item.brand_names.join(", ")}</dd></div>
        )}
      </dl>
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full border-collapse text-[13px]">
          <thead className="bg-muted text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">Indication</th>
              <th className="px-3 py-2 font-medium">PBS Listing</th>
              <th className="px-3 py-2 font-medium">Prescribing conditions</th>
            </tr>
          </thead>
          <tbody>
            {item.listings.length === 0 && (
              <tr className="border-t border-border align-top">
                <td className="px-3 py-2">Any indication</td>
                <td className="px-3 py-2"><PbsListingBadge level={item.restriction_level} /></td>
                <td className="px-3 py-2 text-muted-foreground">—</td>
              </tr>
            )}
            {item.listings.map((listing) => (
              <tr key={listing.restriction_code} className="border-t border-border align-top">
                <td className="px-3 py-2">
                  <div>{listing.indication}</div>
                  {listing.treatment_phase && <div className="text-xs text-muted-foreground">{listing.treatment_phase}</div>}
                </td>
                <td className="px-3 py-2"><PbsListingBadge level={listing.level} /></td>
                <td className="px-3 py-2">
                  {listing.conditions.length === 0 ? <span className="text-muted-foreground">—</span> : (
                    <details>
                      <summary className="cursor-pointer text-xs text-primary">
                        {listing.conditions.length} {listing.conditions.length === 1 ? "condition" : "conditions"}
                      </summary>
                      <ul className="m-0 mt-1 flex list-disc flex-col gap-1 pl-4 text-xs">
                        {listing.conditions.map((condition, index) => <li key={index}>{condition}</li>)}
                      </ul>
                    </details>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
