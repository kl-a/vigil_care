"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { PbsListingBadge } from "@/components/pbs/PbsListingBadge";
import { PbsScheduleNote } from "@/components/pbs/PbsScheduleNote";
import { messageOf } from "@/lib/api";
import {
  backHref, byPrescribingRules, fetchPbsDrug, fetchPbsSchedule, formatMoney, formatScheduleDate, levelsOf, maximumOf,
  type PbsDrug, type PbsItemView, type PbsListingView, type PbsScheduleStatus,
} from "@/lib/pbs";

const TH = "px-3 py-2 font-medium";
const TD = "px-3 py-2";

/**
 * A drug in the PBS Drug Lookup (design doc §5 screen 14, #20, #30), in labelled sections: its PBS Items, when
 * each can be prescribed, and what the patient pays.
 */
export default function PbsDrugPage({ params }: { params: { itemCode: string } }) {
  return (
    <Suspense>
      <PbsDrugView itemCode={params.itemCode} />
    </Suspense>
  );
}

function PbsDrugView({ itemCode }: { itemCode: string }) {
  const back = useSearchParams().get("back");
  const [drug, setDrug] = useState<PbsDrug | null>(null);
  const [schedule, setSchedule] = useState<PbsScheduleStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPbsDrug(itemCode).then(setDrug).catch((reason: unknown) => setError(messageOf(reason)));
    fetchPbsSchedule().then(setSchedule).catch(() => setSchedule(null));
  }, [itemCode]);

  return (
    <div data-screen-label="PBS Drug Lookup" className="flex w-full max-w-[1200px] flex-col gap-5 px-5 pb-8 pt-3">
      <Link href={backHref(back)} className="text-xs text-primary">← Back to results</Link>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {!drug && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {drug && (
        <>
          <header className="flex flex-col gap-1">
            <h1 className="m-0 text-xl font-semibold">{drug.drug_name}</h1>
            <dl className="m-0 flex flex-col gap-0.5 text-[13px]">
              <div className="flex gap-1.5"><dt className="text-muted-foreground">Brands:</dt><dd className="m-0">{drug.brand_names.join(", ") || "No brand name"}</dd></div>
              <div className="flex gap-1.5">
                <dt className="text-muted-foreground">Therapeutic group:</dt>
                <dd className="m-0">{drug.groups.map((group) => group.label).join(", ") || "Not classified"}</dd>
              </div>
            </dl>
          </header>
          <PbsScheduleNote />
          <ItemsOverview items={drug.items} />
          <section aria-labelledby="prescribing" className="flex flex-col gap-3">
            <div className="flex flex-col gap-0.5">
              <h2 id="prescribing" className="m-0 text-base font-semibold">When it can be prescribed</h2>
              <p className="m-0 text-[13px] text-muted-foreground">The PBS Listing for each indication, with the prescribing conditions the PBS sets.</p>
            </div>
            {byPrescribingRules(drug.items).map((rules) => (
              <PrescribingRules key={rules.items.map((item) => item.item_code).join()} items={rules.items} listings={rules.listings} />
            ))}
          </section>
          <PatientPays item={drug.items[0]} schedule={schedule} />
        </>
      )}
    </div>
  );
}

function ItemsOverview({ items }: { items: PbsItemView[] }) {
  return (
    <section aria-labelledby="pbs-items" className="flex flex-col gap-2">
      <div className="flex flex-col gap-0.5">
        <h2 id="pbs-items" className="m-0 text-base font-semibold">PBS Items ({items.length})</h2>
        <p className="m-0 text-[13px] text-muted-foreground">Each PBS Item is one form, strength and pack on one PBS program, with its own item code.</p>
      </div>
      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table aria-label="PBS Items" className="w-full border-collapse text-[13px]">
          <thead className="bg-muted text-left text-xs text-muted-foreground">
            <tr>
              <th className={TH}>Item code</th>
              <th className={TH}>Form and strength</th>
              <th className={TH}>PBS program</th>
              <th className={TH}>Maximum per prescription</th>
              <th className={TH}>Repeats</th>
              <th className={TH}>Listing types</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.item_code} className="border-t border-border align-top">
                <td className={`${TD} font-mono font-semibold`}>{item.item_code}</td>
                <td className={TD}>{item.form ?? "—"}</td>
                <td className={TD}>{item.program_title ?? item.program_code ?? "—"}</td>
                <td className={`${TD} tabular-nums`}>{maximumOf(item)}</td>
                <td className={`${TD} tabular-nums`}>{item.repeats ?? "—"}</td>
                <td className={TD}><span className="flex flex-wrap gap-1">{levelsOf(item).map((level) => <PbsListingBadge key={level} level={level} />)}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PrescribingRules({ items, listings }: { items: PbsItemView[]; listings: PbsListingView[] }) {
  const codes = items.map((item) => item.item_code);
  const title = `${codes.length === 1 ? "PBS Item" : "PBS Items"} ${codes.join(", ")}`;
  return (
    <section aria-label={`When it can be prescribed: ${title}`} className="flex flex-col gap-2 rounded-md border border-border bg-card p-4">
      <h3 className="m-0 text-[13px] font-semibold">
        {title}
        {items.length === 1 && items[0]!.form && <span className="font-normal text-muted-foreground"> · {items[0]!.form}</span>}
      </h3>
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full border-collapse text-[13px]">
          <thead className="bg-muted text-left text-xs text-muted-foreground">
            <tr>
              <th className={TH}>Indication</th>
              <th className={TH}>Treatment phase</th>
              <th className={TH}>PBS Listing</th>
              <th className={TH}>Prescribing conditions</th>
            </tr>
          </thead>
          <tbody>
            {listings.length === 0 && (
              <tr className="border-t border-border align-top">
                <td className={TD}>Any indication</td>
                <td className={`${TD} text-muted-foreground`}>—</td>
                <td className={TD}><PbsListingBadge level={items[0]!.restriction_level} /></td>
                <td className={`${TD} text-muted-foreground`}>None</td>
              </tr>
            )}
            {listings.map((listing) => (
              <tr key={listing.restriction_code} className="border-t border-border align-top">
                <td className={TD}>{listing.indication}</td>
                <td className={TD}>{listing.treatment_phase ?? <span className="text-muted-foreground">—</span>}</td>
                <td className={TD}><PbsListingBadge level={listing.level} /></td>
                <td className={TD}>
                  {listing.conditions.length === 0 ? <span className="text-muted-foreground">None</span> : (
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

/** Co-payments and the Safety Net are the same for every PBS Item in a schedule, so they're shown once. */
function PatientPays({ item, schedule }: { item: PbsItemView | undefined; schedule: PbsScheduleStatus | null }) {
  if (!item) return null;
  return (
    <section aria-labelledby="patient-pays" className="flex flex-col gap-2">
      <h2 id="patient-pays" className="m-0 text-base font-semibold">What the patient pays</h2>
      <dl className="m-0 grid max-w-[70ch] grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[13px] tabular-nums">
        <dt className="text-muted-foreground">Co-payment, general</dt>
        <dd className="m-0">Up to {formatMoney(item.copay_general)} per prescription</dd>
        <dt className="text-muted-foreground">Co-payment, concessional</dt>
        <dd className="m-0">Up to {formatMoney(item.copay_concessional)} per prescription</dd>
        {schedule?.safety_net_general != null && (
          <>
            <dt className="text-muted-foreground">PBS Safety Net</dt>
            <dd className="m-0">
              {formatMoney(schedule.safety_net_general)} general, {formatMoney(schedule.safety_net_concessional)} concessional: once a patient&apos;s PBS spending in a calendar year reaches this threshold, their prescriptions cost less for the rest of that year.
            </dd>
          </>
        )}
      </dl>
      <p className="m-0 text-xs text-muted-foreground">
        The same for every PBS Item in the PBS Schedule of {formatScheduleDate(item.schedule_date)}. The patient pays the co-payment or the item&apos;s price, whichever is less.
      </p>
    </section>
  );
}
