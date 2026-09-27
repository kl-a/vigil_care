"use client";

import { CircleCheck, CircleDot } from "lucide-react";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { PatientOpenItems } from "@/components/openItems/PatientOpenItems";
import { usePatient } from "@/components/patients/PatientContext";
import { SectionSlot } from "@/components/SectionSlot";
import { useViewer } from "@/components/shell/ViewerProvider";
import { SectionCard } from "@/components/ui/SectionCard";
import { StatusPill } from "@/components/ui/StatusPill";
import { FlagWord, NotRecorded, ValueLegend } from "@/components/ui/ValueStates";
import { messageOf } from "@/lib/api";
import {
  CONDITION_STATUS_LABEL, fetchInactiveModuleFacts, INTENT_LABEL, MODALITY_LABEL, NOTE_TYPE_LABEL, scanName, type ClinicalNoteRow, type LabResultRow,
  type ModuleFacts,
} from "@/lib/clinical";
import { formatDate, formatRange, formatUnit } from "@/lib/format";
import { howTaken } from "@/lib/medications";
import { imagingStudyExtensionsFor, sectionsFor, summaryGlanceFor, treatmentCourseExtensionsFor } from "@/lib/modules/registry";
import type { CourseAnnotation, GlanceTile } from "@/lib/modules/types";
import { formatDob } from "@/lib/patients";
import { fetchPatientSummary, type PatientSummary as Summary } from "@/lib/summary";
import { Updated } from "./Updated";

const NONE = <p className="m-0 text-[13px]"><NotRecorded>None recorded</NotRecorded></p>;
const FLAGGED = new Set(["low", "high", "critical"]);

/** One section of the Summary: always shown, "None recorded" when empty (never hidden). */
function Section({ id, title, updated, children }: { id: string; title: string; updated?: ReactNode; children: ReactNode }) {
  return <SectionCard id={id} title={title} meta={updated}>{children}</SectionCard>;
}

/** A small trend with the reference range shaded. */
function Sparkline({ values, low, high }: { values: number[]; low?: number | null; high?: number | null }) {
  if (values.length < 2) return <span className="inline-block w-[80px]" />;
  const all = [...values, ...(low != null ? [low] : []), ...(high != null ? [high] : [])];
  const min = Math.min(...all);
  const span = Math.max(...all) - min || 1;
  const y = (v: number) => 18 - ((v - min) / span) * 16;
  const points = values.map((v, i) => `${(i / (values.length - 1)) * 76 + 2},${y(v)}`).join(" ");
  const last = values[values.length - 1]!;
  const out = (low != null && last < low) || (high != null && last > high);
  return (
    <svg role="img" aria-label="Trend" viewBox="0 0 80 20" className="h-5 w-[80px] text-muted-foreground">
      {(low != null || high != null) && <rect x={0} y={y(high ?? Math.max(...all))} width={80} height={Math.max(y(low ?? min) - y(high ?? Math.max(...all)), 1)} fill="hsl(var(--pos))" opacity={0.12} />}
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth={1.25} />
      <circle cx={78} cy={y(last)} r={2.25} fill={out ? "hsl(var(--neg))" : "currentColor"} />
    </svg>
  );
}

/** Most Recent Results (#53): flagged first, big and in the flag colour; the in-range ones collapsed. */
function LatestLabs({ labs, trends }: { labs: LabResultRow[]; trends: Summary["results"]["lab_trends"] }) {
  const [showAll, setShowAll] = useState(false);
  const flagged = labs.filter((r) => r.flag && FLAGGED.has(r.flag));
  const inRange = labs.filter((r) => !(r.flag && FLAGGED.has(r.flag)));
  const row = (r: LabResultRow) => {
    const out = r.flag && FLAGGED.has(r.flag);
    return (
      <li key={r.id} className="flex items-center justify-between gap-3 border-t border-border py-2 first:border-t-0">
        <span className="flex min-w-0 flex-col">
          <span className="font-medium">{r.analyte}</span>
          <span className="text-xs text-muted-foreground">{formatUnit(r.unit)}{r.unit ? " · " : ""}ref {formatRange(r.ref_low, r.ref_high)}</span>
        </span>
        <span className="flex items-center gap-3">
          <span className="flex flex-col items-end">
            <span className={`text-lg font-semibold tabular-nums leading-tight ${out ? "text-neg" : ""}`}>{r.value ?? r.value_text}</span>
            <FlagWord flag={r.flag} />
          </span>
          <Sparkline values={(trends[r.analyte] ?? []).map((p) => Number(p.value))} low={r.ref_low != null ? Number(r.ref_low) : null} high={r.ref_high != null ? Number(r.ref_high) : null} />
        </span>
      </li>
    );
  };
  return (
    <div className="flex flex-col text-[13px]">
      <ul aria-label="Latest bloods" className="m-0 flex list-none flex-col p-0">
        {flagged.map(row)}
        {showAll && inRange.map(row)}
      </ul>
      {!showAll && inRange.length > 0 && (
        <p className="m-0 flex items-center justify-between gap-2 border-t border-border pt-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1"><CircleCheck aria-hidden className="h-3.5 w-3.5 text-pos" />{inRange.length} within range: {inRange.map((r) => r.analyte).join(", ")}</span>
          <button onClick={() => setShowAll(true)} className="h-6 rounded-md border border-border px-2 text-xs font-medium text-foreground hover:bg-muted">Show</button>
        </p>
      )}
    </div>
  );
}

/** The at-a-glance strip (#53): the Core's tiles and each active module's, in order. */
function GlanceStrip({ tiles }: { tiles: GlanceTile[] }) {
  return (
    <section aria-label="At a glance" className="grid grid-cols-2 overflow-hidden rounded-md border border-border bg-card md:grid-cols-3 xl:grid-cols-5 print:grid-cols-5">
      {[...tiles].sort((a, b) => a.order - b.order).map((t) => (
        <div key={t.key} className="flex flex-col gap-1 border-b border-r border-border p-3 last:border-r-0">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{t.label}</span>
          <span className="text-base font-semibold">{t.value ?? <NotRecorded />}</span>
          {t.detail && <span className="text-xs text-muted-foreground">{t.detail}</span>}
        </div>
      ))}
    </section>
  );
}

function ConditionStatus({ status }: { status: "active" | "resolved" }) {
  const Icon = status === "active" ? CircleDot : CircleCheck;
  return (
    <StatusPill tone={status === "active" ? "cau" : "neu"}>
      <span className="inline-flex items-center gap-1"><Icon aria-hidden className="h-3 w-3" />{CONDITION_STATUS_LABEL[status]}</span>
    </StatusPill>
  );
}

/** Diagnosis when no active module draws it: the inactive modules' facts, read-only in plain words, or "None
 * recorded" (the section is never hidden). */
function DiagnosisFallback({ patientId }: { patientId: string }) {
  const [facts, setFacts] = useState<ModuleFacts[] | null>(null);
  useEffect(() => { fetchInactiveModuleFacts(patientId).then(setFacts).catch(() => setFacts([])); }, [patientId]);
  return (
    <Section id="summary-diagnosis" title="Diagnosis">
      {facts?.length === 0 && NONE}
      {facts?.map((m) => (
        <div key={m.module} className="flex flex-col gap-1 text-[13px]">
          <span className="text-xs text-muted-foreground">{m.display_name} isn&apos;t active at this Practice: its recorded facts, read-only.</span>
          <ul className="m-0 list-disc pl-5">{m.facts.map((f) => <li key={f}>{f}</li>)}</ul>
        </div>
      ))}
    </Section>
  );
}

function Note({ label, note }: { label: string; note: ClinicalNoteRow | null | undefined }) {
  return (
    <div className="flex flex-col gap-0.5 text-[13px]">
      <span className="text-xs font-semibold">{label}</span>
      {note ? (
        <>
          <span className="text-xs text-muted-foreground">{formatDate(note.note_date)}{note.author_name && ` · ${note.author_name}`}{note.recipient_name && ` → ${note.recipient_name}`}</span>
          <p className="m-0 line-clamp-4 whitespace-pre-wrap">{note.content}</p>
        </>
      ) : NONE}
    </div>
  );
}

/**
 * Patient Summary (#47, #53; design doc §5 screen 15): the consultation page. Under the header: an at-a-glance
 * strip and the Open Items; then Diagnosis, Most Recent Results and Recent Treatment first, and the rest. Each
 * section says when it was last updated; an empty one says "None recorded". Prints cleanly.
 */
export function PatientSummary() {
  const { state } = usePatient();
  const { modules } = useViewer();
  const patientId = state.status === "ready" ? state.patient.id : null;
  const [summary, setSummary] = useState<Summary | null>(null);
  const [annotations, setAnnotations] = useState<Record<string, CourseAnnotation>[]>([]);
  const [badges, setBadges] = useState<Record<string, ReactNode>[]>([]);
  const [moduleTiles, setModuleTiles] = useState<GlanceTile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    if (!patientId) return;
    fetchPatientSummary(patientId).then(setSummary).catch((reason: unknown) => setError(messageOf(reason)));
    Promise.all(treatmentCourseExtensionsFor(modules).map((e) => e.load(patientId).catch(() => ({})))).then(setAnnotations);
    Promise.all(imagingStudyExtensionsFor(modules).map((e) => e.load(patientId).catch(() => ({})))).then(setBadges);
    Promise.all(summaryGlanceFor(modules).map((e) => e.load(patientId).catch(() => []))).then((all) => setModuleTiles(all.flat()));
  }, [patientId, modules]);
  useEffect(load, [load]);
  if (state.status !== "ready") return null;
  const { patient } = state;
  const record = (tab: string) => `/patients/${patient.id}/clinical-data?tab=${tab}`;
  const identity = patient.identity;
  const lastIdentityChange = patient.history[0];
  const current = summary?.treatment.courses.find((c) => c.ongoing) ?? summary?.treatment.courses[0];
  const next = summary?.management.next_steps.filter((s) => s.due_date).sort((a, b) => a.due_date!.localeCompare(b.due_date!))[0] ?? summary?.management.next_steps[0];
  const tiles: GlanceTile[] = summary ? [
    ...moduleTiles,
    { key: "treatment", order: 20, label: "Treatment", value: current ? (current.regimen_name ?? current.details?.procedure ?? MODALITY_LABEL[current.modality]) : null,
      detail: current && (current.ongoing ? `since ${formatDate(current.start_date)} · ongoing` : `${formatDate(current.start_date)} – ${formatDate(current.end_date)}`) },
    { key: "next-step", order: 50, label: "Next step", value: next?.description ?? null, detail: next?.due_date ? `due ${formatDate(next.due_date)}` : null },
  ] : [];
  return (
    <div data-screen-label="Patient Summary" className="flex w-full max-w-[1400px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ValueLegend />
        <button onClick={() => window.print()} className="h-7 rounded-md border border-border bg-card px-2.5 text-xs font-medium hover:bg-muted" data-noprint>Print summary</button>
      </div>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {summary === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading the Summary…</p>}
      {summary && (
        <>
          <GlanceStrip tiles={tiles} />
          <PatientOpenItems key={summary.open_items.map((i) => i.subject_id).join()} patientId={patient.id} initial={summary.open_items} cards />
          <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2 xl:grid-cols-3 print:grid-cols-2">
            <div className="flex flex-col gap-4">
              {sectionsFor("patient-summary", modules).length > 0 ? <SectionSlot slot="patient-summary" /> : <DiagnosisFallback patientId={patient.id} />}
            </div>

            <Section id="summary-results" title="Most Recent Results" updated={<Updated updated={summary.results.updated} href={record("labs")} />}>
              {summary.results.latest_labs.length === 0 ? NONE : <LatestLabs labs={summary.results.latest_labs} trends={summary.results.lab_trends} />}
            </Section>

            <Section id="summary-treatment" title="Recent Treatment" updated={<Updated updated={summary.treatment.updated} href={record("treatment")} />}>
              {summary.treatment.courses.length === 0 ? NONE : (
                <ul className="m-0 flex list-none flex-col gap-3 p-0 text-[13px]">
                  {summary.treatment.courses.map((c) => (
                    <li key={c.id} className="flex flex-col gap-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold">{c.regimen_name ?? c.details?.procedure ?? MODALITY_LABEL[c.modality]}</span>
                        {annotations.map((a, i) => a[c.id] && <span key={i} title={a[c.id]!.detail}>{a[c.id]!.badge ?? <span className="rounded border border-border px-1.5 text-xs font-semibold">{a[c.id]!.label}</span>}</span>)}
                      </span>
                      <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-0.5 text-[13px]">
                        <dt className="text-muted-foreground">Intent</dt><dd className="m-0">{MODALITY_LABEL[c.modality]}{c.intent && ` · ${INTENT_LABEL[c.intent]}`}</dd>
                        <dt className="text-muted-foreground">Dates</dt><dd className="m-0">{formatDate(c.start_date)} – {c.ongoing ? "ongoing" : formatDate(c.end_date)}</dd>
                        {c.regimen_drugs.length > 0 && <><dt className="text-muted-foreground">Regimen</dt><dd className="m-0">{c.regimen_drugs.map((d) => d.drug).join(" + ")}</dd></>}
                        {c.reason_stopped && <><dt className="text-muted-foreground">Stopped</dt><dd className="m-0">{c.reason_stopped}</dd></>}
                      </dl>
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            <Section id="summary-imaging" title="Imaging" updated={<Updated updated={summary.results.updated} href={record("imaging")} />}>
              {summary.results.scans.length === 0 ? NONE : summary.results.scans.map((s) => (
                <div key={s.id} className="flex flex-col gap-0.5 border-t border-border pt-2 text-[13px] first:border-t-0 first:pt-0">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{scanName(s)}</span><span className="text-xs text-muted-foreground">{formatDate(s.study_date)}</span>
                    {badges.map((b, i) => b[s.id] && <span key={i}>{b[s.id]}</span>)}
                  </span>
                  {s.findings.filter((f) => f.is_new || f.is_measurable).map((f) => (
                    <span key={f.id} className="text-xs">{f.is_new ? "New: " : ""}{f.description}{f.site && `, ${f.site}`}{f.size_mm && ` (${f.size_mm} mm)`}</span>
                  ))}
                </div>
              ))}
            </Section>

            <Section id="summary-management" title="Management" updated={<Updated updated={summary.management.updated} href={record("plan")} />}>
              {summary.management.plan ? (
                <figure className="m-0 flex flex-col gap-1">
                  <blockquote className="m-0 whitespace-pre-wrap border-l-2 border-border pl-3 text-[13px]">&ldquo;{summary.management.plan.plan_text}&rdquo;</blockquote>
                  <figcaption className="text-xs text-muted-foreground">
                    Management Plan{summary.management.plan.author_name && `, ${summary.management.plan.author_name}`}{summary.management.plan.plan_date && `, ${formatDate(summary.management.plan.plan_date)}`} (verbatim)
                  </figcaption>
                </figure>
              ) : NONE}
              <span className="text-xs font-semibold">Next Steps</span>
              {summary.management.next_steps.length === 0 ? NONE : (
                <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[13px]">
                  {summary.management.next_steps.map((s) => <li key={s.id}>{s.description}{s.due_date && <span className="text-xs text-muted-foreground"> · due {formatDate(s.due_date)}</span>}</li>)}
                </ul>
              )}
            </Section>

            <Section id="summary-notes" title="Clinical Notes" updated={<Updated updated={summary.notes.updated} href={record("plan")} />}>
              <Note label="Most recent note" note={summary.notes.latest_note} />
              <Note label={`Most recent ${NOTE_TYPE_LABEL.letter_to_referrer.toLowerCase()}`} note={summary.notes.latest_letter} />
            </Section>

            <Section id="summary-history" title="Medical History" updated={<Updated updated={summary.history.updated} href={record("conditions")} />}>
              <span className="text-xs font-semibold">Comorbidities</span>
              {summary.history.comorbidities.length === 0 ? NONE : (
                <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[13px]">
                  {summary.history.comorbidities.map((c) => (
                    <li key={c.id} className="flex items-center gap-2">{c.name}<ConditionStatus status={c.status} /></li>
                  ))}
                </ul>
              )}
              <span className="text-xs font-semibold">Current Medications</span>
              {summary.history.medications.length === 0 ? NONE : (
                <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[13px]">
                  {summary.history.medications.map((m) => <li key={m.id}><span className="font-medium">{m.drug_name}</span> <span className="text-xs text-muted-foreground">{formatUnit(howTaken(m))}</span></li>)}
                </ul>
              )}
            </Section>

            <Section id="summary-registration" title="Registration"
              updated={lastIdentityChange && <Updated updated={{ by: lastIdentityChange.by_display_name, job_title: lastIdentityChange.by_job_title, at: lastIdentityChange.at }}
                href={`/patients/${patient.id}/overview`} />}>
              <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-[13px]">
                {([["Name", patient.display_name], ["Date of birth (age)", formatDob(identity.dob)], ["Medicare number", identity.medicare_number],
                  ["Address", identity.address], ["Phone", identity.phone], ["Mobile", identity.mobile]] as const).map(([label, value]) => (
                  <div key={label} className="contents"><dt className="text-muted-foreground">{label}</dt><dd className="m-0">{value ?? "—"}</dd></div>
                ))}
              </dl>
            </Section>
          </div>
        </>
      )}
    </div>
  );
}
