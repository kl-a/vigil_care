"use client";

import { useCallback, useEffect, useState } from "react";
import { StatusPill, type Tone } from "@/components/ui/StatusPill";
import { messageOf } from "@/lib/api";
import { fetchHealth, type Health } from "@/lib/system";

function Check({ label, value, tone, detail }: { label: string; value: string; tone: Tone; detail: string }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-border bg-card p-4">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <StatusPill tone={tone}>{value}</StatusPill>
      <span className="text-xs text-muted-foreground">{detail}</span>
    </div>
  );
}

/** System status (support view, design doc §6.4): open to every Job Title; IDs and states only, never Patient data. */
export default function SystemStatusPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);

  const check = useCallback(() => {
    fetchHealth()
      .then((result) => { setHealth(result); setError(null); })
      .catch((reason: unknown) => { setHealth(null); setError(messageOf(reason)); })
      .finally(() => setCheckedAt(new Date()));
  }, []);

  useEffect(check, [check]);

  return (
    <div data-screen-label="System status" className="flex w-full max-w-[1100px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="m-0 text-xl font-semibold">System status</h1>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {checkedAt && <span>Checked {checkedAt.toLocaleTimeString("en-AU")}</span>}
          <button onClick={check} className="h-7 rounded-md border border-border px-2 text-xs text-foreground hover:bg-muted">Check again</button>
        </div>
      </div>
      {error && <p role="alert" className="m-0 rounded-md border border-neg-bd bg-neg-bg p-3 text-[13px] text-neg">The backend isn&apos;t answering. {error}</p>}
      {!health && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Checking…</p>}
      {health && (
        <>
          <p className="m-0 text-[13px]">
            {health.status === "ok" ? "Everything Vigil needs is running." : "Vigil is degraded: see below."}
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Check
              label="Database"
              value={health.database === "ok" ? "OK" : "Unreachable"}
              tone={health.database === "ok" ? "pos" : "neg"}
              detail={health.database === "ok" ? "PostgreSQL is answering." : "Patient data can't be read or saved until it's back."}
            />
            <Check
              label="VLM worker"
              value={health.vlm_worker === "configured" ? "Configured" : "Not configured"}
              tone={health.vlm_worker === "configured" ? "pos" : "neu"}
              detail="Reads hard pages locally. Not needed until documents are processed (Stage 8)."
            />
            <Check
              label="Environment"
              value={health.environment.toUpperCase()}
              tone={health.environment === "dev" ? "cau" : "neu"}
              detail={health.environment === "dev" ? "Development: synthetic data only." : "Test: automated tests and the Reference Set."}
            />
          </div>
        </>
      )}
    </div>
  );
}
