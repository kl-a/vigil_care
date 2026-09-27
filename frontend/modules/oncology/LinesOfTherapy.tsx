"use client";

import { useState, type FormEvent } from "react";
import { FIELD } from "@/components/ui/styles";
import { messageOf, request, type Schemas } from "@/lib/api";
import type { CourseAnnotation, TreatmentCourseExtension } from "@/lib/modules/types";

type LineOfTherapy = Schemas["LineOfTherapy"];

export const fetchLinesOfTherapy = (patientId: string) => request<LineOfTherapy[]>(`/patients/${patientId}/lines-of-therapy`);
export const overrideLineOfTherapy = (patientId: string, courseId: string, line: number | null, reason: string) =>
  request<LineOfTherapy[]>(`/patients/${patientId}/treatment-courses/${courseId}/line-of-therapy`, { method: "PUT", body: JSON.stringify({ line, reason }) });

export function ordinal(n: number): string {
  const suffix = n % 100 >= 10 && n % 100 <= 20 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th";
  return `${n}${suffix}`;
}

/** Each palliative systemic course's Line of Therapy, as the Core's Treatment Courses show it. */
async function load(patientId: string): Promise<Record<string, CourseAnnotation>> {
  const lines = await fetchLinesOfTherapy(patientId);
  return Object.fromEntries(lines.map((l) => [l.treatment_course_id, { label: `${ordinal(l.line)} line`, detail: l.explanation, overridden: l.overridden, value: l.line }]));
}

/** A clinician sets a course's line (e.g. maintenance isn't a new line), or derives it again; always with why. */
function LineEditor({ patientId, courseId, annotation, onSaved, onCancel }: {
  patientId: string; courseId: string; annotation: CourseAnnotation | undefined; onSaved: () => void; onCancel: () => void;
}) {
  const [line, setLine] = useState(String(annotation?.value ?? 1));
  const [derive, setDerive] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try { await overrideLineOfTherapy(patientId, courseId, derive ? null : Number(line), reason.trim()); onSaved(); } catch (e) { setError(messageOf(e)); }
  }
  return (
    <form aria-label="Line of Therapy" onSubmit={submit} className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-background p-3">
      <label className="flex flex-col gap-1 text-xs font-medium">Line<input type="number" min={1} max={20} disabled={derive} value={line} onChange={(e) => setLine(e.target.value)} className={`${FIELD} w-20`} /></label>
      {annotation?.overridden && (
        <label className="inline-flex items-center gap-1.5 text-[13px]"><input type="checkbox" checked={derive} onChange={(e) => setDerive(e.target.checked)} />Derive it again</label>
      )}
      <label className="flex flex-col gap-1 text-xs font-medium">Reason (required)<input required value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Maintenance of 1st line" className={`${FIELD} w-72`} /></label>
      {error && <p role="alert" className="m-0 w-full text-[13px] text-neg">{error}</p>}
      <button type="submit" disabled={!reason.trim()} className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground disabled:opacity-50">Save</button>
      <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
    </form>
  );
}

/** Line of Therapy (#40): derived from the palliative systemic courses by start date; clinicians may override. */
export const lineOfTherapyExtension: TreatmentCourseExtension = { load, edit: { factKind: "line_of_therapy_override", label: "Change line", Editor: LineEditor } };
