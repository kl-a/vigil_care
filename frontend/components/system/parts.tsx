"use client";

import { useEffect, useState, type ReactNode } from "react";
import { StatusPill, type Tone } from "@/components/ui/StatusPill";
import { messageOf } from "@/lib/api";

const STATUS: Record<string, { label: string; tone: Tone }> = {
  queued: { label: "Queued", tone: "neu" },
  running: { label: "Running", tone: "cau" },
  succeeded: { label: "Succeeded", tone: "pos" },
  failed: { label: "Failed", tone: "neg" },
  cancelled: { label: "Cancelled", tone: "neu" },
};

/** A Job's or pipeline run's state. */
export function RunStatus({ status }: { status: string }) {
  const { label, tone } = STATUS[status] ?? { label: status, tone: "neu" as Tone };
  return <StatusPill tone={tone}>{label}</StatusPill>;
}

/** Loads a Support View, and again whenever `version` changes (e.g. a Refresh was started). */
export function useSupportView<T>(load: () => Promise<T>, version: number): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let current = true;
    load()
      .then((result) => { if (current) { setData(result); setError(null); } })
      .catch((reason: unknown) => { if (current) setError(messageOf(reason)); });
    return () => { current = false; };
  }, [load, version]);
  return { data, error };
}

/** A Support View's section: heading, one line on what it shows, then loading, error, empty or the table. */
export function SupportSection<T>({ id, title, about, empty, rows, error, children }: {
  id: string;
  title: string;
  about: string;
  empty: string;
  rows: T[] | null;
  error: string | null;
  children: (rows: T[]) => ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <h2 id={id} className="m-0 text-sm font-semibold">{title}</h2>
      <p className="m-0 max-w-[70ch] text-[13px] text-muted-foreground">{about}</p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {rows === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading…</p>}
      {rows && rows.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">{empty}</p>}
      {rows && rows.length > 0 && <div className="overflow-x-auto rounded-md border border-border">{children(rows)}</div>}
    </section>
  );
}

export const TABLE = "w-full border-collapse text-[13px]";
export const HEAD = "bg-muted text-left text-xs text-muted-foreground";
export const TH = "px-3 py-2 font-medium";
export const TD = "px-3 py-2 align-top";
export const IDS = "px-3 py-2 align-top font-mono text-xs text-muted-foreground";
