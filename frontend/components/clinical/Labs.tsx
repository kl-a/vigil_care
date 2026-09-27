"use client";

import { ArrowDown, ArrowUp, TriangleAlert } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { RowMenu } from "@/components/ui/RowMenu";
import { SectionCard } from "@/components/ui/SectionCard";
import { FIELD } from "@/components/ui/styles";
import { SubTabs } from "@/components/ui/SubTabs";
import { FlagWord, NotRecorded } from "@/components/ui/ValueStates";
import { VerifiedMark } from "@/components/ui/Verified";
import { messageOf } from "@/lib/api";
import {
  addLabPanel, COMMON_PANELS, fetchEntryRights, fetchLabResults, removeLabResult, trendsOf, type LabFlag, type LabResultRow,
  type NewLabResult,
} from "@/lib/clinical";
import { formatDate, todayIso } from "@/lib/dates";
import { formatRange, formatUnit } from "@/lib/format";
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
  const [view, setView] = useState<"trend" | "report">("trend");

  const load = useCallback(() => {
    fetchLabResults(patientId).then(setResults).catch((reason: unknown) => setError(messageOf(reason)));
  }, [patientId]);
  useEffect(load, [load]);
  useEffect(() => {
    fetchEntryRights().then((rights) => setCanEnter(Boolean(rights.lab_result))).catch(() => setCanEnter(false));
  }, []);

  const trends = useMemo(() => trendsOf(results ?? []), [results]);
  const charted = analyte ?? [...trends.keys()][0] ?? null;
  const reports = new Set((results ?? []).map((r) => r.panel_id ?? r.collected_at)).size;
  const remove = (result: LabResultRow) => canEnter && (
    <RowMenu label={`${result.analyte} ${formatDate(result.collected_at)}`} items={[{ label: "Remove", danger: true, onSelect: () => setRemoving(result) }]} />
  );

  return (
    <SectionCard id="labs" title="Labs" action={canEnter ? (!entering && <button onClick={() => setEntering(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium text-foreground hover:bg-muted">Enter results</button>) : <EntryLock />}>
      {entering && <PanelForm onCancel={() => setEntering(false)} onSave={async (panel) => { await addLabPanel(patientId, panel); setEntering(false); load(); }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {results === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading results…</p>}
      {results?.length === 0 && <p className="m-0 text-[13px]"><NotRecorded>None recorded</NotRecorded></p>}
      {results && results.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <SubTabs label="Labs view" tabs={[{ key: "trend", label: "Trend" }, { key: "report", label: "Full report" }]} current={view} onChange={setView} />
            <span className="text-xs text-muted-foreground">{trends.size} {trends.size === 1 ? "test" : "tests"} · {reports} {reports === 1 ? "report" : "reports"}</span>
          </div>
          {view === "trend" && charted && (
            <>
              <div role="group" aria-label="Analyte" className="flex flex-wrap items-center gap-1.5">
                <span className="mr-1 text-xs text-muted-foreground">Analyte</span>
                {[...trends.entries()].map(([name, series]) => {
                  const flag = series[series.length - 1]?.flag;
                  const Arrow = flag === "high" ? ArrowUp : flag === "low" ? ArrowDown : null;
                  return (
                    <button key={name} onClick={() => setAnalyte(name)} aria-pressed={charted === name}
                      className={`inline-flex h-7 items-center gap-1 rounded-full border px-3 text-xs font-medium ${charted === name ? "border-primary/40 bg-accent text-primary" : "border-border bg-card hover:bg-muted"}`}>
                      {name}{Arrow && <Arrow aria-label={`latest ${flag}`} className="h-3 w-3 text-neg" />}
                    </button>
                  );
                })}
              </div>
              <p className="m-0 text-[13px]"><span className="font-semibold">{charted}</span>{" "}
                <span className="text-xs text-muted-foreground">{formatUnit(trends.get(charted)!.at(-1)?.unit)} · reference {formatRange(trends.get(charted)!.at(-1)?.ref_low, trends.get(charted)!.at(-1)?.ref_high)}</span>
              </p>
              <TrendChart analyte={charted} results={trends.get(charted)!} />
              <ResultsTable label={`${charted} results`} rows={[...trends.get(charted)!].reverse()} analyte={false} action={remove} />
            </>
          )}
          {view === "report" && <ResultsTable label="Lab results" rows={results} analyte action={remove} />}
        </>
      )}
      {removing && (
        <ReasonDialog title={`Remove ${removing.analyte} (${formatDate(removing.collected_at.slice(0, 10))})`} actor={signOffName(me)} confirmLabel="Remove result" danger
          onConfirm={async (reason) => { await removeLabResult(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">For a value recorded by mistake. The audit trail keeps what it was, who removed it and why.</p>
        </ReasonDialog>
      )}
    </SectionCard>
  );
}

/** Results as a table: date, (panel and analyte), value in the flag colour, Flag in words, reference range, ✓. */
function ResultsTable({ label, rows, analyte, action }: { label: string; rows: LabResultRow[]; analyte: boolean; action: (row: LabResultRow) => ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table aria-label={label} className="w-full border-collapse text-[13px]">
        <thead className="bg-muted text-left text-xs text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Date</th>
            {analyte && <th className="px-3 py-2 font-medium">Panel</th>}
            {analyte && <th className="px-3 py-2 font-medium">Analyte</th>}
            <th className="px-3 py-2 font-medium">Value</th>
            <th className="px-3 py-2 font-medium">Flag</th>
            <th className="px-3 py-2 font-medium">Reference</th>
            <th className="px-3 py-2 font-medium">Verified</th>
            <th className="px-3 py-2"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((result) => {
            const flagged = result.flag === "low" || result.flag === "high" || result.flag === "critical";
            return (
              <tr key={result.id} className="border-t border-border">
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDate(result.collected_at.slice(0, 10))}</td>
                {analyte && <td className="px-3 py-2 text-muted-foreground">{result.panel ?? "—"}</td>}
                {analyte && <td className="px-3 py-2">{result.analyte}</td>}
                <td className={`whitespace-nowrap px-3 py-2 tabular-nums ${flagged ? "font-semibold text-neg" : ""}`}>
                  {result.value ?? result.value_text} {formatUnit(result.unit)}{result.flag && FLAG[result.flag] && <FlagMark flag={FLAG[result.flag]!} />}
                </td>
                <td className="px-3 py-2">{flagged ? <FlagWord flag={result.flag} /> : "—"}</td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums text-muted-foreground">{formatRange(result.ref_low, result.ref_high)}</td>
                <td className="px-3 py-2"><VerifiedMark subjectTable="lab_result" subjectId={result.id} entered={result.entered} /></td>
                <td className="whitespace-nowrap px-3 py-2 text-right">{action(result)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** A lab result's flag: colour, icon and letter together. None for a normal result. */
export function LabFlagMark({ flag }: { flag: LabFlag | null | undefined }) {
  const mark = flag ? FLAG[flag] : undefined;
  return mark ? <FlagMark flag={mark} /> : null;
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

const WIDTH = 1000;
const HEIGHT = 200;
const PAD = { left: 44, right: 12, top: 12, bottom: 24 };

/** One analyte over time with its reference range shaded (the latest range entered, as ranges rarely change
 * for a lab). Numbers only. */
export function TrendChart({ analyte, results }: { analyte: string; results: LabResultRow[] }) {
  const points = results.filter((r) => r.value !== null).map((r) => ({
    at: Date.parse(r.collected_at), value: Number(r.value), flagged: r.flag === "low" || r.flag === "high" || r.flag === "critical",
  }));
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
      <svg role="img" aria-label={`${analyte} trend`} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full text-muted-foreground">
        {(low !== null || high !== null) && (
          // A one-sided range (e.g. eGFR >60) is shaded to the chart's edge.
          <rect data-testid="reference-band" x={PAD.left} y={y(high ?? max)} width={WIDTH - PAD.left - PAD.right}
            height={Math.max(y(low ?? min) - y(high ?? max), 1)} fill="hsl(var(--pos))" opacity={0.1} />
        )}
        <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="currentColor" strokeWidth={1} />
        <text x={PAD.left - 6} y={y(max) + 4} textAnchor="end" fontSize={10} fill="currentColor">{max}</text>
        <text x={PAD.left - 6} y={y(min) + 4} textAnchor="end" fontSize={10} fill="currentColor">{min}</text>
        {/* Data, not an action: a neutral line; points outside the range in the negative colour. */}
        <polyline points={points.map((p) => `${x(p.at)},${y(p.value)}`).join(" ")} fill="none" stroke="hsl(var(--foreground))" strokeOpacity={0.55} strokeWidth={2} vectorEffect="non-scaling-stroke" />
        {points.map((p) => (
          <circle key={p.at} cx={x(p.at)} cy={y(p.value)} r={4} fill={p.flagged ? "hsl(var(--neg))" : "hsl(var(--foreground))"} fillOpacity={p.flagged ? 1 : 0.55}>
            <title>{`${p.value}${p.flagged ? " (outside range)" : ""}`}</title>
          </circle>
        ))}
      </svg>
    </div>
  );
}
