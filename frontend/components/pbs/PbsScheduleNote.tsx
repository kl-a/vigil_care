"use client";

import { TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { messageOf } from "@/lib/api";
import { fetchPbsSchedule, formatScheduleDate, type PbsScheduleStatus } from "@/lib/pbs";
import { formatWhen } from "@/lib/users";

/**
 * Which PBS Schedule the lookup shows ("as of" its date), with a warning when it's the Sample Schedule (out of
 * date, demo only) or the last Refresh failed (design doc §10.2: the previous schedule stays visible).
 */
export function PbsScheduleNote() {
  const [status, setStatus] = useState<PbsScheduleStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPbsSchedule().then(setStatus).catch((reason: unknown) => setError(messageOf(reason)));
  }, []);

  if (error) return <p className="m-0 text-[13px] text-neg">{error}</p>;
  if (!status) return null;
  if (!status.current) {
    return (
      <p className="m-0 text-[13px] text-muted-foreground">
        No PBS Schedule has been loaded yet. The worker refreshes it on the 1st of each month; a developer admin can start a PBS Refresh from System status.
      </p>
    );
  }
  const failed = status.last_refresh?.status === "failed";
  return (
    <div className="flex flex-col gap-2">
      <p className="m-0 text-[13px] text-muted-foreground">
        PBS Schedule of {formatScheduleDate(status.schedule_date)}{status.is_sample ? " (Sample Schedule)" : ""}, loaded {formatWhen(status.current.refreshed_at)}.
      </p>
      {(status.is_sample || failed) && (
        <div role="alert" className="flex flex-col gap-1 rounded-md border border-cau-bd bg-cau-bg px-3 py-2 text-[13px] text-cau">
          {status.is_sample && (
            <p className="m-0 flex items-start gap-1.5">
              <TriangleAlert aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                <strong>Sample data from the PBS Schedule of {formatScheduleDate(status.schedule_date)}: out of date, for demos only. Don&apos;t use it for clinical decisions.</strong>{" "}
                A copy bundled with Vigil, shown because the PBS Schedule API couldn&apos;t be reached or no API key is set.
              </span>
            </p>
          )}
          {failed && (
            <p className="m-0 flex items-start gap-1.5">
              <TriangleAlert aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span><strong>The last PBS Refresh failed</strong> ({formatWhen(status.last_refresh?.refreshed_at)}). Showing the schedule as of {formatScheduleDate(status.schedule_date)}.</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
