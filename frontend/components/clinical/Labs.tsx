"use client";

import { ArrowDown, ArrowUp, TriangleAlert } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import {
  addLabPanel, COMMON_PANELS, fetchEntryRights, fetchLabResults, removeLabResult, trendsOf, type LabFlag, type LabResultRow,
  type NewLabResult,
} from "@/lib/clinical";
import { formatDate, todayIso } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";

type Row = { analyte: string; value: string; unit: string; ref_low: string; ref_high: string };
const blankRow = (analyte = "", unit = ""): Row => ({ analyte, value: "", unit, ref_low: "", ref_high: "" });

/** Colour, icon and label together (frontend-design principle 6); "normal" needs no mark. */
const FLAG: Partial<Record<LabFlag, { letter: string; label: string; icon: typeof ArrowDown }>> = {
  low: { letter: "L", label: "low", icon: ArrowDown },
  high: { letter: "H", label: "high", icon: ArrowUp },
  critical: { letter: "!!", label: "critical", icon: TriangleAlert },
};

/** A number, or text for results that aren't a plain number (e.g. "<5"). */
function asResult(row: Row): NewLabResult | null {
  const value = row.value.trim();
  if (!row.analyte.trim() || !value) return null;
  const numeric = /^-?\d+(\.\d+)?$/.test(value);
  const range = (text: string) => (text.trim() ? text.trim() : null);
  return {
    analyte: row.analyte.trim(), unit: row.unit.trim() || null, ref_low: range(row.ref_low), ref_high: range(row.ref_high),
    ...(numeric ? { value } : { value_text: value }),
  } as NewLabResult;
}

/**
 * Bloods and other labs (#42, design doc §5 screen 9): entered as a panel in one save, each value flagged H or L
 * from the report's own reference range, and a trend per analyte with its range shaded.
 */
export function Labs({ patientId }: { patientId: string }) {
  const me = useSignedInUser();
  const [results, setResults] = useState<LabResultRow[] | null>(null);
  const [canEnter, setCanEnter] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entering, setEntering] = useState(false);
  const [removing, setRemoving] = useState<LabResultRow | null>(null);
  const [analyte, setAnalyte] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchLabResults(patientId).then(setResults).catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId]);
  useEffect(load, [load]);
  useEffect(() => {
    fetchEntryRights().then((rights) => setCanEnter(Boolean(rights.lab_result))).catch(() => setCanEnter(false));
  }, []);

  const trends = useMemo(() => trendsOf(results ?? []), [results]);
  const charted = analyte ?? [...trends.keys()][0] ?? null;

  return (
    <section aria-labelledby="labs" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id="labs" className="m-0 text-sm font-semibold">Labs</h2>
        {canEnter ? (
          !entering && <button onClick={() => setEntering(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Enter results</button>
        ) : (
          <EntryLock />
        )}
      </div>
      {entering && <PanelForm onCancel={() => setEntering(false)} onSave={async (panel) => { await addLabPanel(patientId, panel); setEntering(false); load(); }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {results === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading results…</p>}
      {results?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {charted && trends.get(charted) && (
        <div className="flex flex-col gap-2">
          <label className="flex w-fit flex-col gap-1 text-xs font-medium">
            Trend
            <select value={charted} onChange={(e) => setAnalyte(e.target.value)} className={`${FIELD} w-56`}>
              {[...trends.keys()].map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </label>
          <TrendChart analyte={charted} results={trends.get(charted)!} />
        </div>
      )}
      {results && results.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border">
          <table aria-label="Lab results" className="w-full border-collapse text-[13px]">
            <thead className="bg-muted text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Collected</th>
                <th className="px-3 py-2 font-medium">Panel</th>
                <th className="px-3 py-2 font-medium">Analyte</th>
                <th className="px-3 py-2 text-right font-medium">Result</th>
                <th className="px-3 py-2 font-medium">Reference range</th>
                {canEnter && <th className="px-3 py-2 font-medium"><span className="sr-only">Actions</span></th>}
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr key={result.id} className="border-t border-border align-top">
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDate(result.collected_at.slice(0, 10))}</td>
                  <td className="px-3 py-2 text-muted-foreground">{result.panel ?? "—"}</td>
                  <td className="px-3 py-2">{result.analyte}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                    <span className={result.flag === "low" || result.flag === "high" ? "font-semibold text-cau" : ""}>
                      {result.value ?? result.value_text} {result.unit ?? ""}
                    </span>
                    {result.flag && FLAG[result.flag] && <FlagMark flag={FLAG[result.flag]!} />}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums text-muted-foreground">
                    {result.ref_low ?? result.ref_high ? `${result.ref_low ?? ""}–${result.ref_high ?? ""}` : "—"}
                  </td>
                  {canEnter && (
                    <td className="whitespace-nowrap px-3 py-2 text-right">
                      <button onClick={() => setRemoving(result)} className="text-xs font-medium text-neg">Remove</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {removing && (
        <ReasonDialog title={`Remove ${removing.analyte} (${formatDate(removing.collected_at.slice(0, 10))})`} actor={signOffName(me)} confirmLabel="Remove result" danger
          onConfirm={async (reason) => { await removeLabResult(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">For a value recorded by mistake. The audit trail keeps what it was, who removed it and why.</p>
        </ReasonDialog>
      )}
    </section>
  );
}

function FlagMark({ flag }: { flag: { letter: string; label: string; icon: typeof ArrowDown } }) {
  const Icon = flag.icon;
  return (
    <span aria-label={flag.label} className="ml-1 inline-flex items-center gap-0.5 text-xs font-semibold text-cau">
      <Icon aria-hidden className="h-3 w-3" />{flag.letter}
    </span>
  );
}

function PanelForm({ onCancel, onSave }: { onCancel: () => void; onSave: (panel: { collected_on: string; collected_time: string | null; panel: string | null; results: NewLabResult[] }) => Promise<void> }) {
  const [collectedOn, setCollectedOn] = useState(todayIso());
  const [collectedTime, setCollectedTime] = useState("");
  const [panel, setPanel] = useState("");
  const [rows, setRows] = useState<Row[]>([blankRow()]);
  const [error, setError] = useState<string | null>(null);

  function choosePanel(name: string) {
    setPanel(name);
    const common = COMMON_PANELS[name];
    if (common) setRows(common.map(({ analyte, unit }) => blankRow(analyte, unit)));
  }
  const set = (index: number, field: keyof Row, value: string) =>
    setRows((current) => current.map((row, i) => (i === index ? { ...row, [field]: value } : row)));

  async function submit(event: FormEvent) {
    event.preventDefault();
    const results = rows.map(asResult).filter((result): result is NewLabResult => result !== null);
    if (results.length === 0) { setError("Enter at least one result."); return; }
    setError(null);
    try {
      await onSave({ collected_on: collectedOn, collected_time: collectedTime || null, panel: panel.trim() || null, results });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }

  return (
    <form aria-label="Enter results" onSubmit={submit} className="flex flex-col gap-3 rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium">Collected on<input type="date" required value={collectedOn} onChange={(e) => setCollectedOn(e.target.value)} className={`${FIELD} w-40`} /></label>
        <label className="flex flex-col gap-1 text-xs font-medium">Time (optional)<input type="time" value={collectedTime} onChange={(e) => setCollectedTime(e.target.value)} className={`${FIELD} w-28`} /></label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Panel
          <input list="common-panels" value={panel} onChange={(e) => choosePanel(e.target.value)} placeholder="e.g. FBC" className={`${FIELD} w-40`} />
          <datalist id="common-panels">{Object.keys(COMMON_PANELS).map((name) => <option key={name} value={name} />)}</datalist>
        </label>
      </div>
      <p className="m-0 text-xs text-muted-foreground">Type each reference range from the report: flags come from it. Leave a value empty to skip that analyte.</p>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead className="text-left text-xs text-muted-foreground">
            <tr><th className="py-1 pr-2 font-medium">Analyte</th><th className="py-1 pr-2 font-medium">Result</th><th className="py-1 pr-2 font-medium">Unit</th><th className="py-1 pr-2 font-medium">Ref low</th><th className="py-1 font-medium">Ref high</th></tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                {(["analyte", "value", "unit", "ref_low", "ref_high"] as const).map((field) => (
                  <td key={field} className="py-1 pr-2">
                    <input aria-label={`${row.analyte || "Analyte"} ${field.replace("_", " ")}`} value={row[field]} onChange={(e) => set(index, field, e.target.value)} className={FIELD} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div><button type="button" onClick={() => setRows((current) => [...current, blankRow()])} className="text-xs font-medium text-primary">Add a row</button></div>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Save panel</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}

const WIDTH = 560;
const HEIGHT = 160;
const PAD = { left: 44, right: 12, top: 12, bottom: 24 };

/** One analyte over time with its reference range shaded (the latest range entered, as ranges rarely change
 * for a lab). Numbers only. */
export function TrendChart({ analyte, results }: { analyte: string; results: LabResultRow[] }) {
  const points = results.filter((r) => r.value !== null).map((r) => ({ at: Date.parse(r.collected_at), value: Number(r.value) }));
  if (points.length === 0) return <p className="m-0 text-[13px] text-muted-foreground">No numeric results to chart for {analyte}.</p>;
  const latest = results[results.length - 1]!;
  const low = latest.ref_low !== null ? Number(latest.ref_low) : null;
  const high = latest.ref_high !== null ? Number(latest.ref_high) : null;
  const values = [...points.map((p) => p.value), ...(low !== null ? [low] : []), ...(high !== null ? [high] : [])];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const first = points[0]!.at;
  const last = points[points.length - 1]!.at;
  const x = (at: number) => PAD.left + (last === first ? 0.5 : (at - first) / (last - first)) * (WIDTH - PAD.left - PAD.right);
  const y = (value: number) => PAD.top + (1 - (value - min) / span) * (HEIGHT - PAD.top - PAD.bottom);
  return (
    <div className="overflow-x-auto">
      <svg role="img" aria-label={`${analyte} trend`} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-40 w-full max-w-[560px] text-muted-foreground">
        {(low !== null || high !== null) && (
          // A one-sided range (e.g. eGFR >60) is shaded to the chart's edge.
          <rect data-testid="reference-band" x={PAD.left} y={y(high ?? max)} width={WIDTH - PAD.left - PAD.right}
            height={Math.max(y(low ?? min) - y(high ?? max), 1)} fill="currentColor" opacity={0.12} />
        )}
        <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="currentColor" strokeWidth={1} />
        <text x={PAD.left - 6} y={y(max) + 4} textAnchor="end" fontSize={10} fill="currentColor">{max}</text>
        <text x={PAD.left - 6} y={y(min) + 4} textAnchor="end" fontSize={10} fill="currentColor">{min}</text>
        <polyline points={points.map((p) => `${x(p.at)},${y(p.value)}`).join(" ")} fill="none" stroke="hsl(var(--primary))" strokeWidth={2} />
        {points.map((p) => <circle key={p.at} cx={x(p.at)} cy={y(p.value)} r={3} fill="hsl(var(--primary))" />)}
      </svg>
    </div>
  );
}
