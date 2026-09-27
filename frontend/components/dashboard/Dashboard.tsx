"use client";

import { useCallback, useEffect, useState } from "react";
import { OpenItemTable } from "@/components/openItems/OpenItemList";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { SectionCard } from "@/components/ui/SectionCard";
import { TableCard } from "@/components/ui/TableCard";
import { messageOf } from "@/lib/api";
import { formatDate, formatWhen } from "@/lib/format";
import { listRefreshes, type RefreshView } from "@/lib/jobs";
import { fetchPbsSchedule, type PbsScheduleStatus } from "@/lib/pbs";
import { fetchOpenItems, mayAct, WHO_LABEL, type OpenItem, type Who } from "@/lib/summary";

const CHIP = "h-7 rounded-full border px-3 text-xs font-medium";
// A selected filter is a state, not an action: neutral, not the primary colour (frontend-design §4.1).
const chip = (on: boolean) => `${CHIP} ${on ? "border-foreground bg-muted text-foreground" : "border-border text-muted-foreground hover:bg-muted"}`;

/**
 * Dashboard (#48, #54; design doc §5 screen 2): the Practice's Open Items as a table, filtered by type and by who
 * can act, with the reference data beside it. Only this Practice's; the developer admin's Dashboard is System status.
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
    <div data-screen-label="Dashboard" className="flex w-full max-w-[1400px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="m-0 text-xl font-semibold">Open Items</h1>
        {items && <span className="text-[13px] text-muted-foreground">{items.length} across the practice</span>}
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_260px]">
        <div className="flex min-w-0 flex-col gap-2">
          <TableCard label="Open Items" count={items ? `${shown.length} shown` : undefined} toolbar={items && items.length > 0 && (
            <div className="flex flex-col gap-2">
              <div role="group" aria-label="Filter by type" className="flex flex-wrap gap-2">
                <button onClick={() => setType(null)} aria-pressed={type === null} className={chip(type === null)}>All ({items.length})</button>
                {types.map(([k, label]) => (
                  <button key={k} onClick={() => setType(k)} aria-pressed={type === k} className={chip(type === k)}>{label} ({items.filter((i) => i.type === k).length})</button>
                ))}
              </div>
              <div role="group" aria-label="Filter by who can act" className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted-foreground">Who can act</span>
                <button onClick={() => setWho(null)} aria-pressed={who === null} className={chip(who === null)}>Anyone</button>
                <button onClick={() => setWho("mine")} aria-pressed={who === "mine"} className={chip(who === "mine")}>I can act</button>
                {(["clinician", "staff"] as const).map((w) => (
                  <button key={w} onClick={() => setWho(w)} aria-pressed={who === w} className={chip(who === w)}>{WHO_LABEL[w]}</button>
                ))}
              </div>
            </div>
          )}>
            {error && <p role="alert" className="m-0 p-3 text-[13px] text-neg">{error}</p>}
            {items === null && !error && <p role="status" className="m-0 p-3 text-[13px] text-muted-foreground">Loading Open Items…</p>}
            {items && <OpenItemTable items={shown} onActed={load} />}
          </TableCard>
          <p className="m-0 text-xs text-muted-foreground">Each clears when it&apos;s done; nothing is dismissed.</p>
        </div>
        <ReferenceData />
      </div>
    </div>
  );
}

/** The rail: which PBS Schedule Vigil is showing, and each Refresh's last run. */
function ReferenceData() {
  const [schedule, setSchedule] = useState<PbsScheduleStatus | null>(null);
  const [refreshes, setRefreshes] = useState<RefreshView[] | null>(null);
  useEffect(() => {
    fetchPbsSchedule().then(setSchedule).catch(() => setSchedule(null));
    listRefreshes().then(setRefreshes).catch(() => setRefreshes([]));
  }, []);
  return (
    <SectionCard id="reference-data" title="Reference data" className="self-start">
      <dl className="m-0 flex flex-col gap-2 text-[13px]">
        <div className="flex items-baseline justify-between gap-2">
          <dt>PBS Schedule</dt>
          <dd className="m-0 text-right text-muted-foreground">
            {schedule?.schedule_date ? `${formatDate(schedule.schedule_date)}${schedule.is_sample ? " (sample)" : ""}` : "Not loaded"}
          </dd>
        </div>
        {refreshes?.map((r) => (
          <div key={r.kind} className="flex items-baseline justify-between gap-2">
            {/* The kind's name without its schedule note, e.g. "Refresh the PBS Schedule". */}
            <dt title={r.description}>{r.description.split(" (")[0]}</dt>
            <dd className={`m-0 text-right text-xs ${r.last_job?.status === "failed" ? "text-neg" : "text-muted-foreground"}`}>
              {r.last_job ? `${r.last_job.status === "failed" ? "Failed" : "Last run"} ${formatWhen(r.last_job.finished_at ?? r.last_job.created_at)}` : "Never run"}
            </dd>
          </div>
        ))}
      </dl>
    </SectionCard>
  );
}
