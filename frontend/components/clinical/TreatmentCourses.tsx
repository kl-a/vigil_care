"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { useSignedInUser, useViewer } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import {
  addTreatmentCourse, changeTreatmentCourse, fetchConditions, fetchEntryRights, fetchTreatmentCourses, INTENT_LABEL, MODALITY_LABEL,
  removeTreatmentCourse, type ConditionRow, type Intent, type Modality, type NewTreatmentCourse, type TreatmentCourseRow,
} from "@/lib/clinical";
import { formatDate, todayIso } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";
import { treatmentCourseExtensionsFor } from "@/lib/modules/registry";
import type { CourseAnnotation, TreatmentCourseExtension } from "@/lib/modules/types";

/**
 * Treatment Courses (#40, design doc §5 screen 9): every course of treatment for a Condition (Core): systemic
 * with its Regimen, surgery or radiation. Active modules add their view of a course (e.g. its Line of Therapy).
 */
export function TreatmentCourses({ patientId, compact = false }: { patientId: string; compact?: boolean }) {
  const me = useSignedInUser();
  const { modules } = useViewer();
  const extensions = treatmentCourseExtensionsFor(modules);
  const [courses, setCourses] = useState<TreatmentCourseRow[] | null>(null);
  const [annotations, setAnnotations] = useState<Record<string, CourseAnnotation>[]>([]);
  const [rights, setRights] = useState<Record<string, boolean>>({});
  const [adding, setAdding] = useState(false);
  const [ending, setEnding] = useState<TreatmentCourseRow | null>(null);
  const [removing, setRemoving] = useState<TreatmentCourseRow | null>(null);
  const [editing, setEditing] = useState<{ edit: NonNullable<TreatmentCourseExtension["edit"]>; course: TreatmentCourseRow; annotation?: CourseAnnotation } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    fetchTreatmentCourses(patientId).then(setCourses).catch((reason: unknown) => setError(messageOf(reason)));
    // Each module's view on its own: one that fails to load leaves the others shown.
    Promise.all(extensions.map((extension) => extension.load(patientId).catch(() => ({})))).then(setAnnotations);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- extensions follow the active modules
  }, [patientId, modules]);
  useEffect(load, [load]);
  useEffect(() => { fetchEntryRights().then(setRights).catch(() => setRights({})); }, []);
  // The Overview's timeline is read-only; entry happens on the Clinical Data tab.
  const canEnter = !compact && Boolean(rights.treatment_course);

  return (
    <section aria-labelledby="treatment-courses" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id="treatment-courses" className="m-0 text-sm font-semibold">Treatment Courses</h2>
        {canEnter ? !adding && <button onClick={() => setAdding(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Add course</button> : !compact && <EntryLock />}
      </div>
      {adding && <CourseForm patientId={patientId} onCancel={() => setAdding(false)} onSave={async (course) => { await addTreatmentCourse(patientId, course); setAdding(false); load(); }} />}
      {editing && (
        <editing.edit.Editor patientId={patientId} courseId={editing.course.id} annotation={editing.annotation}
          onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {courses?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {courses && courses.length > 0 && (
        <ol aria-label="Treatment Courses" className="m-0 flex list-none flex-col divide-y divide-border p-0">
          {courses.map((course) => (
            <li key={course.id} className="flex flex-col gap-1 py-2 text-[13px]">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{course.regimen_name ?? course.details?.procedure ?? course.details?.site ?? MODALITY_LABEL[course.modality]}</span>
                  <StatusPill tone="neu">{MODALITY_LABEL[course.modality]}{course.intent && ` · ${INTENT_LABEL[course.intent]}`}</StatusPill>
                  {extensions.map((extension, index) => {
                    const annotation = annotations[index]?.[course.id];
                    return annotation && (annotation.badge ? <span key={index} title={annotation.detail}>{annotation.badge}</span> : (
                      <span key={index} title={annotation.detail} className="rounded-full border border-border px-2 py-0.5 text-xs font-semibold">
                        {annotation.label}
                      </span>
                    ));
                  })}
                </span>
                <span className="inline-flex gap-2">
                  {!compact && extensions.map(({ edit }, index) => edit && rights[edit.factKind] && annotations[index]?.[course.id] && (
                    <button key={index} onClick={() => setEditing({ edit, course, annotation: annotations[index]?.[course.id] })} className="text-xs font-medium text-primary">
                      {edit.label}
                    </button>
                  ))}
                  {canEnter && course.ongoing && <button onClick={() => setEnding(course)} className="text-xs font-medium text-primary">End course</button>}
                  {canEnter && <button onClick={() => setRemoving(course)} className="text-xs font-medium text-neg">Remove</button>}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                For {course.condition_name} · {formatDate(course.start_date)} – {course.ongoing ? "ongoing" : formatDate(course.end_date)}
                {course.reason_stopped && ` (${course.reason_stopped})`}
              </span>
              {course.regimen_drugs.length > 0 && (
                <span className="text-xs">{course.regimen_drugs.map((d) => `${d.drug}${d.dose ? ` ${d.dose}` : ""}`).join(" + ")}</span>
              )}
              {extensions.map((_, index) => annotations[index]?.[course.id] && (
                <span key={index} className="text-xs text-muted-foreground">{annotations[index]![course.id]!.detail}</span>
              ))}
            </li>
          ))}
        </ol>
      )}
      {ending && <EndCourse course={ending} actor={signOffName(me)} onClose={() => setEnding(null)}
        onEnd={async (end, why, reason) => { await changeTreatmentCourse(patientId, ending.id, { end_date: end, reason_stopped: why || null, reason }); setEnding(null); load(); }} />}
      {removing && (
        <ReasonDialog title="Remove this Treatment Course" actor={signOffName(me)} confirmLabel="Remove course" danger
          onConfirm={async (reason) => { await removeTreatmentCourse(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">For a course recorded by mistake. To record that it ended, use End course instead.</p>
        </ReasonDialog>
      )}
    </section>
  );
}

function EndCourse({ course, actor, onClose, onEnd }: {
  course: TreatmentCourseRow; actor: string; onClose: () => void; onEnd: (end: string, why: string, reason: string) => Promise<void>;
}) {
  const [end, setEnd] = useState(todayIso());
  const [why, setWhy] = useState("");
  return (
    <ReasonDialog title={`End ${course.regimen_name ?? MODALITY_LABEL[course.modality]}`} actor={actor} confirmLabel="End course"
      onConfirm={async (reason) => onEnd(end, why, reason ?? "")} onClose={onClose}>
      <label className="flex flex-col gap-1 text-xs font-medium">Ended on<input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className={FIELD} /></label>
      <label className="flex flex-col gap-1 text-xs font-medium">Why it stopped<input value={why} onChange={(e) => setWhy(e.target.value)} placeholder="e.g. Completed, progression, toxicity" className={FIELD} /></label>
    </ReasonDialog>
  );
}

type Drug = { drug: string; dose: string };

function CourseForm({ patientId, onCancel, onSave }: { patientId: string; onCancel: () => void; onSave: (course: NewTreatmentCourse) => Promise<void> }) {
  const [conditions, setConditions] = useState<ConditionRow[]>([]);
  const [condition, setCondition] = useState("");
  const [modality, setModality] = useState<Modality>("systemic");
  const [intent, setIntent] = useState<Intent | "">("");
  const [regimen, setRegimen] = useState("");
  const [drugs, setDrugs] = useState<Drug[]>([{ drug: "", dose: "" }]);
  const [detailA, setDetailA] = useState("");
  const [detailB, setDetailB] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetchConditions(patientId).then((rows) => { setConditions(rows); setCondition((c) => c || rows[0]?.id || ""); }).catch(() => setConditions([]));
  }, [patientId]);
  // Surgery: procedure and margins; radiation: site and dose.
  const detailLabels = modality === "surgery" ? ["procedure", "margins"] : ["site", "dose"];
  async function submit(event: FormEvent) {
    event.preventDefault();
    const details = modality === "systemic" ? null : Object.fromEntries([[detailLabels[0]!, detailA.trim()], [detailLabels[1]!, detailB.trim()]].filter(([, v]) => v));
    try {
      await onSave({
        condition_id: condition, modality, intent: intent || null, start_date: start || null, end_date: end || null,
        regimen_name: modality === "systemic" ? regimen.trim() || null : null,
        regimen_drugs: modality === "systemic" ? drugs.filter((d) => d.drug.trim()).map((d) => ({ drug: d.drug.trim(), dose: d.dose.trim() || null })) : [],
        details: details && Object.keys(details).length > 0 ? details : null,
      });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  if (conditions.length === 0) return <p className="m-0 text-[13px] text-muted-foreground">Add a Condition first: a course is given for one.</p>;
  return (
    <form aria-label="New Treatment Course" onSubmit={submit} className="flex flex-col gap-3 rounded-md border border-border bg-background p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs font-medium">
          For
          <select value={condition} onChange={(e) => setCondition(e.target.value)} className={FIELD}>
            {conditions.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Modality
          <select value={modality} onChange={(e) => setModality(e.target.value as Modality)} className={FIELD}>
            {Object.entries(MODALITY_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Intent
          <select value={intent} onChange={(e) => setIntent(e.target.value as Intent | "")} className={FIELD}>
            <option value="">Not recorded</option>{Object.entries(INTENT_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-xs font-medium">Start<input type="date" value={start} onChange={(e) => setStart(e.target.value)} className={FIELD} /></label>
          <label className="flex flex-col gap-1 text-xs font-medium">End<input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className={FIELD} /></label>
        </div>
      </div>
      {modality === "systemic" ? (
        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
          <legend className="mb-1 text-xs font-semibold">Regimen</legend>
          <label className="flex flex-col gap-1 text-xs font-medium">Name<input value={regimen} onChange={(e) => setRegimen(e.target.value)} placeholder="e.g. Carboplatin + pemetrexed" className={`${FIELD} max-w-md`} /></label>
          {drugs.map((d, i) => (
            <div key={i} className="flex gap-2">
              <input aria-label={`Drug ${i + 1}`} value={d.drug} onChange={(e) => setDrugs((all) => all.map((x, j) => (j === i ? { ...x, drug: e.target.value } : x)))} placeholder="Drug" className={`${FIELD} w-56`} />
              <input aria-label={`Dose ${i + 1}`} value={d.dose} onChange={(e) => setDrugs((all) => all.map((x, j) => (j === i ? { ...x, dose: e.target.value } : x)))} placeholder="Planned dose" className={`${FIELD} w-40`} />
            </div>
          ))}
          <div><button type="button" onClick={() => setDrugs((all) => [...all, { drug: "", dose: "" }])} className="text-xs font-medium text-primary">Add a drug</button></div>
        </fieldset>
      ) : (
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col gap-1 text-xs font-medium capitalize">{detailLabels[0]}<input value={detailA} onChange={(e) => setDetailA(e.target.value)} className={`${FIELD} w-64`} /></label>
          <label className="flex flex-col gap-1 text-xs font-medium capitalize">{detailLabels[1]}<input value={detailB} onChange={(e) => setDetailB(e.target.value)} className={`${FIELD} w-48`} /></label>
        </div>
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Add course</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}
