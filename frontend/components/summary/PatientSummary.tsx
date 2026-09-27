"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { LabFlagMark } from "@/components/clinical/Labs";
import { PatientOpenItems } from "@/components/openItems/PatientOpenItems";
import { usePatient } from "@/components/patients/PatientContext";
import { SectionSlot } from "@/components/SectionSlot";
import { useViewer } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { Updated } from "./Updated";
import { CircleCheck, CircleDot } from "lucide-react";
import { messageOf } from "@/lib/api";
import { CONDITION_STATUS_LABEL, fetchInactiveModuleFacts, INTENT_LABEL, MODALITY_LABEL, NOTE_TYPE_LABEL, scanName, type ClinicalNoteRow, type ModuleFacts } from "@/lib/clinical";
import { formatDate } from "@/lib/dates";
import { howTaken } from "@/lib/medications";
import { imagingStudyExtensionsFor, sectionsFor, treatmentCourseExtensionsFor } from "@/lib/modules/registry";
import type { CourseAnnotation } from "@/lib/modules/types";
import { formatUnit } from "@/lib/format";
import { formatDob } from "@/lib/patients";
import { fetchPatientSummary, type PatientSummary as Summary } from "@/lib/summary";

const NONE = <p className="m-0 text-[13px] text-muted-foreground">None recorded</p>;

/** One section of the Summary: always shown, "None recorded" when empty (never hidden). */
function Section({ id, title, updated, children }: { id: string; title: string; updated?: ReactNode; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex break-inside-avoid flex-col gap-2 rounded-md border border-border bg-card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={id} className="m-0 text-sm font-semibold">{title}</h2>
        {updated}
      </div>
      {children}
    </section>
  );
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  const points = values.map((v, i) => `${(i / (values.length - 1)) * 56 + 2},${14 - ((v - min) / span) * 12}`).join(" ");
  return (
    <svg role="img" aria-label="Trend" viewBox="0 0 60 16" className="h-4 w-[60px] text-muted-foreground">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth={1.5} />
    </svg>
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
 * Patient Summary (#47, design doc §5 screen 15): the consultation page. Registration, Diagnosis (from the
 * Specialty Modules), Most Recent Results, Recent Treatment, Clinical Notes, Management, Medical History and Open
 * Items. Each section says when it was last updated; an empty one says "None recorded". Prints cleanly.
 */
export function PatientSummary() {
  const { state } = usePatient();
  const { modules } = useViewer();
  const patientId = state.status === "ready" ? state.patient.id : null;
  const [summary, setSummary] = useState<Summary | null>(null);
  const [annotations, setAnnotations] = useState<Record<string, CourseAnnotation>[]>([]);
  const [badges, setBadges] = useState<Record<string, ReactNode>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    if (!patientId) return;
    fetchPatientSummary(patientId).then(setSummary).catch((reason: unknown) => setError(messageOf(reason)));
    Promise.all(treatmentCourseExtensionsFor(modules).map((e) => e.load(patientId).catch(() => ({})))).then(setAnnotations);
    Promise.all(imagingStudyExtensionsFor(modules).map((e) => e.load(patientId).catch(() => ({})))).then(setBadges);
  }, [patientId, modules]);
  useEffect(load, [load]);
  if (state.status !== "ready") return null;
  const { patient } = state;
  const record = (tab: string) => `/patients/${patient.id}/clinical-data?tab=${tab}`;
  const identity = patient.identity;
  const lastIdentityChange = patient.history[0];
  return (
    <div data-screen-label="Patient Summary" className="flex w-full max-w-[1400px] flex-col gap-4 px-5 pb-8 pt-3">
      <div className="flex items-center justify-between gap-3" data-noprint>
        <p className="m-0 text-xs text-muted-foreground">At a glance, for the consultation.</p>
        <button onClick={() => window.print()} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Print</button>
      </div>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 print:grid-cols-2">
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

        <div className="flex flex-col gap-4">
          {sectionsFor("patient-summary", modules).length > 0 ? <SectionSlot slot="patient-summary" /> : <DiagnosisFallback patientId={patient.id} />}
        </div>

        {summary === null && !error && <p role="status" className="m-0 text-[13px] text-muted-foreground">Loading the Summary…</p>}
        {summary && (
          <>
            <Section id="summary-results" title="Most Recent Results" updated={<Updated updated={summary.results.updated} href={record("labs")} />}>
              {summary.results.latest_labs.length === 0 && summary.results.scans.length === 0 && NONE}
              {summary.results.latest_labs.length > 0 && (
                <table aria-label="Latest bloods" className="w-full border-collapse text-[13px]">
                  <tbody>
                    {summary.results.latest_labs.map((r) => (
                      <tr key={r.id} className="border-t border-border first:border-t-0">
                        <td className="py-1 pr-2">{r.analyte}</td>
                        <td className="py-1 pr-2 tabular-nums">{r.value ?? r.value_text} {formatUnit(r.unit)}<LabFlagMark flag={r.flag} /></td>
                        <td className="py-1 pr-2"><Sparkline values={(summary.results.lab_trends[r.analyte] ?? []).map((p) => Number(p.value))} /></td>
                        <td className="py-1 text-right text-xs text-muted-foreground">{formatDate(r.collected_at.slice(0, 10))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {summary.results.scans.map((s) => (
                <div key={s.id} className="flex flex-col gap-0.5 border-t border-border pt-2 text-[13px]">
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

            <Section id="summary-treatment" title="Recent Treatment" updated={<Updated updated={summary.treatment.updated} href={record("treatment")} />}>
              {summary.treatment.courses.length === 0 ? NONE : (
                <ul className="m-0 flex list-none flex-col gap-2 p-0 text-[13px]">
                  {summary.treatment.courses.map((c) => (
                    <li key={c.id} className="flex flex-col gap-0.5">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{c.regimen_name ?? c.details?.procedure ?? MODALITY_LABEL[c.modality]}</span>
                        <StatusPill tone="neu">{MODALITY_LABEL[c.modality]}{c.intent && ` · ${INTENT_LABEL[c.intent]}`}</StatusPill>
                        {annotations.map((a, i) => a[c.id] && <span key={i} title={a[c.id]!.detail}>{a[c.id]!.badge ?? <span className="text-xs font-semibold">{a[c.id]!.label}</span>}</span>)}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {c.condition_name} · {formatDate(c.start_date)} – {c.ongoing ? "ongoing" : formatDate(c.end_date)}
                        {c.regimen_drugs.length > 0 && ` · ${c.regimen_drugs.map((d) => d.drug).join(" + ")}`}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            <Section id="summary-notes" title="Clinical Notes" updated={<Updated updated={summary.notes.updated} href={record("plan")} />}>
              <Note label="Most recent note" note={summary.notes.latest_note} />
              <Note label={`Most recent ${NOTE_TYPE_LABEL.letter_to_referrer.toLowerCase()}`} note={summary.notes.latest_letter} />
            </Section>

            <Section id="summary-management" title="Management" updated={<Updated updated={summary.management.updated} href={record("plan")} />}>
              {summary.management.plan ? (
                <figure className="m-0 flex flex-col gap-1">
                  <figcaption className="text-xs text-muted-foreground">
                    Management Plan{summary.management.plan.author_name && `, ${summary.management.plan.author_name}`}{summary.management.plan.plan_date && `, ${formatDate(summary.management.plan.plan_date)}`} (verbatim)
                  </figcaption>
                  <blockquote className="m-0 whitespace-pre-wrap border-l-2 border-border pl-3 text-[13px]">{summary.management.plan.plan_text}</blockquote>
                </figure>
              ) : NONE}
              <span className="text-xs font-semibold">Next Steps</span>
              {summary.management.next_steps.length === 0 ? NONE : (
                <ul className="m-0 flex list-none flex-col gap-1 p-0 text-[13px]">
                  {summary.management.next_steps.map((s) => <li key={s.id}>{s.description}{s.due_date && <span className="text-xs text-muted-foreground"> · due {formatDate(s.due_date)}</span>}</li>)}
                </ul>
              )}
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
                  {summary.history.medications.map((m) => <li key={m.id}><span className="font-medium">{m.drug_name}</span> <span className="text-xs text-muted-foreground">{howTaken(m)}</span></li>)}
                </ul>
              )}
            </Section>

            <PatientOpenItems key={summary.open_items.map((i) => i.subject_id).join()} patientId={patient.id} initial={summary.open_items} />
          </>
        )}
      </div>
    </div>
  );
}
