"use client";

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { EnteredBy } from "@/components/clinical/Conditions";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { useSignedInUser, useViewer } from "@/components/shell/ViewerProvider";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import {
  addFinding, addImagingStudy, changeImagingStudy, changesBetween, fetchConditions, fetchEntryRights, fetchImagingStudies, removeFinding, removeImagingStudy, scanName,
  type ConditionRow, type FindingRow, type ImagingStudyRow, type NewFinding, type NewImagingStudy,
} from "@/lib/clinical";
import { formatDate, todayIso } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";
import { imagingStudyExtensionsFor } from "@/lib/modules/registry";

/** A yes/no/not stated answer, as the report gives it. */
const yesNo = (value: boolean | null | undefined) => (value === true ? "Yes" : value === false ? "No" : "—");

/**
 * Imaging & Findings (#43, design doc §5 screen 9): each scan with its report's impression, verbatim, and its
 * Findings. Active modules add a badge to a scan (e.g. its Response Assessment).
 */
export function Imaging({ patientId }: { patientId: string }) {
  const me = useSignedInUser();
  const { modules } = useViewer();
  const extensions = imagingStudyExtensionsFor(modules);
  const [studies, setStudies] = useState<ImagingStudyRow[] | null>(null);
  const [badges, setBadges] = useState<Record<string, ReactNode>[]>([]);
  const [rights, setRights] = useState<Record<string, boolean>>({});
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<{ study: ImagingStudyRow; finding?: FindingRow } | null>(null);
  const [correcting, setCorrecting] = useState<ImagingStudyRow | null>(null);
  const [saving, setSaving] = useState<{ study: ImagingStudyRow; change: Partial<StudyValues> } | null>(null);
  const [addingTo, setAddingTo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    fetchImagingStudies(patientId).then(setStudies).catch((reason: unknown) => setError(messageOf(reason)));
    Promise.all(extensions.map((extension) => extension.load(patientId).catch(() => ({})))).then(setBadges);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- extensions follow the active modules
  }, [patientId, modules]);
  useEffect(load, [load]);
  useEffect(() => { fetchEntryRights().then(setRights).catch(() => setRights({})); }, []);
  const canEnter = Boolean(rights.imaging_study);
  const canEnterFindings = Boolean(rights.finding);

  return (
    <section aria-labelledby="imaging" className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id="imaging" className="m-0 text-sm font-semibold">Imaging &amp; Findings</h2>
        {canEnter ? !adding && <button onClick={() => setAdding(true)} className="h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted">Add scan</button> : <EntryLock />}
      </div>
      {adding && <StudyForm patientId={patientId} withFindings={canEnterFindings} onCancel={() => setAdding(false)}
        onSave={async (study) => { await addImagingStudy(patientId, study); setAdding(false); load(); }} />}
      {correcting && <StudyForm patientId={patientId} withFindings={false} initial={correcting} onCancel={() => setCorrecting(null)}
        onSave={async ({ findings: _, ...values }) => {
          const change = changesBetween(studyValuesOf(correcting), values);
          // Nothing changed: nothing to sign off, so no reason to ask for.
          if (Object.keys(change).length > 0) setSaving({ study: correcting, change });
          setCorrecting(null);
        }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {studies?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {studies?.map((study, index) => (
        <article key={study.id} aria-label={`${scanName(study)}, ${formatDate(study.study_date)}`} className="flex flex-col gap-2 border-t border-border pt-3 first-of-type:border-t-0 first-of-type:pt-0">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex flex-wrap items-center gap-2 text-[13px]">
              <span className="font-medium">{scanName(study)}</span>
              <span>{formatDate(study.study_date)}</span>
              {index === 0 && <span className="text-xs text-muted-foreground">(latest)</span>}
              {badges.map((byStudy, i) => byStudy[study.id] && <span key={i}>{byStudy[study.id]}</span>)}
            </span>
            <span className="inline-flex gap-2">
              {canEnterFindings && addingTo !== study.id && <button onClick={() => setAddingTo(study.id)} className="text-xs font-medium text-primary">Add finding</button>}
              {canEnter && <button onClick={() => { setCorrecting(study); setAdding(false); }} className="text-xs font-medium text-primary">Correct</button>}
              {canEnter && <button onClick={() => setRemoving({ study })} className="text-xs font-medium text-neg">Remove</button>}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            {study.comparison_date && `Compared with ${formatDate(study.comparison_date)} · `}Entered by <EnteredBy entered={study.entered} />
          </span>
          {study.impression && (
            <figure className="m-0 flex flex-col gap-1">
              <figcaption className="text-xs font-semibold">Impression (as reported)</figcaption>
              <blockquote className="m-0 whitespace-pre-wrap border-l-2 border-border pl-3 text-[13px]">{study.impression}</blockquote>
            </figure>
          )}
          {study.findings.length > 0 && (
            <table aria-label="Findings" className="w-full border-collapse text-left text-[13px]">
              <thead className="text-xs text-muted-foreground">
                <tr><th className="py-1 font-medium">Site</th><th className="font-medium">Finding</th><th className="font-medium">Size</th><th className="font-medium">SUVmax</th><th className="font-medium">New?</th><th className="font-medium">Measurable?</th><th className="font-medium">Attributed to</th><th /></tr>
              </thead>
              <tbody>
                {study.findings.map((f) => (
                  <tr key={f.id} className="border-t border-border">
                    <td className="py-1">{[f.site, f.laterality].filter(Boolean).join(", ") || "—"}</td>
                    <td>{f.description}</td>
                    <td>{f.size_mm ? `${f.size_mm} mm` : "—"}</td>
                    <td>{f.suv_max ?? "—"}</td>
                    <td>{yesNo(f.is_new)}</td>
                    <td>{yesNo(f.is_measurable)}</td>
                    <td>{f.condition_name ?? "—"}</td>
                    <td className="text-right">{canEnterFindings && <button onClick={() => setRemoving({ study, finding: f })} className="text-xs font-medium text-neg">Remove</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {addingTo === study.id && <FindingForm patientId={patientId} onCancel={() => setAddingTo(null)}
            onSave={async (finding) => { await addFinding(patientId, study.id, finding); setAddingTo(null); load(); }} />}
        </article>
      ))}
      {saving && (
        <ReasonDialog title={`Save changes to ${scanName(saving.study)}`} actor={signOffName(me)} confirmLabel="Save"
          onConfirm={async (reason) => { await changeImagingStudy(patientId, saving.study.id, { ...saving.change, reason: reason ?? "" }); setSaving(null); load(); }}
          onClose={() => setSaving(null)} />
      )}
      {removing && (
        <ReasonDialog title={removing.finding ? "Remove this Finding" : "Remove this scan"} actor={signOffName(me)} confirmLabel="Remove" danger
          onConfirm={async (reason) => {
            if (removing.finding) await removeFinding(patientId, removing.study.id, removing.finding.id, reason ?? "");
            else await removeImagingStudy(patientId, removing.study.id, reason ?? "");
            setRemoving(null); load();
          }}
          onClose={() => setRemoving(null)}>
          <p className="m-0 text-[13px] text-muted-foreground">{removing.finding ? "For a Finding entered by mistake." : "For a scan entered by mistake; its Findings go with it."}</p>
        </ReasonDialog>
      )}
    </section>
  );
}

type FindingDraft = { site: string; laterality: string; description: string; size_mm: string; suv_max: string; is_new: string; is_measurable: string; condition_id: string };
const EMPTY_FINDING: FindingDraft = { site: "", laterality: "", description: "", size_mm: "", suv_max: "", is_new: "", is_measurable: "", condition_id: "" };
const answer = (value: string) => (value === "yes" ? true : value === "no" ? false : null);

/** A Finding as the API takes it; blank ones are left out. */
export function findingOf(d: FindingDraft): NewFinding | null {
  if (!d.description.trim()) return null;
  return {
    description: d.description.trim(), site: d.site.trim() || null, laterality: (d.laterality || null) as NewFinding["laterality"],
    size_mm: d.size_mm || null, suv_max: d.suv_max || null, is_new: answer(d.is_new), is_measurable: answer(d.is_measurable),
    condition_id: d.condition_id || null,
  };
}

type StudyValues = Omit<NewImagingStudy, "findings">;

function studyValuesOf(study: ImagingStudyRow): StudyValues {
  return { modality: study.modality, body_region: study.body_region ?? null, study_date: study.study_date, comparison_date: study.comparison_date ?? null, impression: study.impression ?? null };
}

const SMALL = `${FIELD} h-7 text-xs`;

/** One Finding's inputs, as a row: in a new scan's form, or added to a scan later. */
function FindingInputs({ n, finding: f, conditions, set }: { n: number; finding: FindingDraft; conditions: ConditionRow[]; set: (field: keyof FindingDraft, value: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-8">
      <input aria-label={`Site ${n}`} value={f.site} onChange={(e) => set("site", e.target.value)} placeholder="Site" className={SMALL} />
      <select aria-label={`Side ${n}`} value={f.laterality} onChange={(e) => set("laterality", e.target.value)} className={SMALL}>
        <option value="">Side</option><option value="left">Left</option><option value="right">Right</option><option value="bilateral">Bilateral</option>
      </select>
      <input aria-label={`Finding ${n}`} value={f.description} onChange={(e) => set("description", e.target.value)} placeholder="Finding" className={`${SMALL} sm:col-span-2`} />
      <input aria-label={`Size (mm) ${n}`} type="number" min="0.1" step="0.1" value={f.size_mm} onChange={(e) => set("size_mm", e.target.value)} placeholder="Size mm" className={SMALL} />
      <input aria-label={`SUVmax ${n}`} type="number" min="0" step="0.01" value={f.suv_max} onChange={(e) => set("suv_max", e.target.value)} placeholder="SUVmax" className={SMALL} />
      <select aria-label={`New ${n}`} value={f.is_new} onChange={(e) => set("is_new", e.target.value)} className={SMALL}>
        <option value="">New?</option><option value="yes">New</option><option value="no">Not new</option>
      </select>
      <select aria-label={`Measurable ${n}`} value={f.is_measurable} onChange={(e) => set("is_measurable", e.target.value)} className={SMALL}>
        <option value="">Measurable?</option><option value="yes">Measurable</option><option value="no">Not measurable</option>
      </select>
      <select aria-label={`Attributed to ${n}`} value={f.condition_id} onChange={(e) => set("condition_id", e.target.value)} className={`${SMALL} col-span-2 sm:col-span-8 sm:w-72`}>
        <option value="">Not attributed (only if the report says so)</option>
        {conditions.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
    </div>
  );
}

function useConditions(patientId: string): ConditionRow[] {
  const [conditions, setConditions] = useState<ConditionRow[]>([]);
  useEffect(() => { fetchConditions(patientId).then(setConditions).catch(() => setConditions([])); }, [patientId]);
  return conditions;
}

function FindingForm({ patientId, onCancel, onSave }: { patientId: string; onCancel: () => void; onSave: (finding: NewFinding) => Promise<void> }) {
  const conditions = useConditions(patientId);
  const [draft, setDraft] = useState<FindingDraft>({ ...EMPTY_FINDING });
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const finding = findingOf(draft);
    if (!finding) { setError("Describe the Finding."); return; }
    try { await onSave(finding); } catch (reason) { setError(messageOf(reason)); }
  }
  return (
    <form aria-label="New Finding" onSubmit={submit} className="flex flex-col gap-2 rounded-md border border-border bg-background p-3">
      <FindingInputs n={1} finding={draft} conditions={conditions} set={(field, value) => setDraft((d) => ({ ...d, [field]: value }))} />
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Add finding</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}

function StudyForm({ patientId, withFindings, initial, onCancel, onSave }: {
  patientId: string; withFindings: boolean; initial?: ImagingStudyRow; onCancel: () => void; onSave: (study: NewImagingStudy) => Promise<void>;
}) {
  const conditions = useConditions(patientId);
  const [modality, setModality] = useState(initial?.modality ?? "CT");
  const [region, setRegion] = useState(initial?.body_region ?? "");
  const [date, setDate] = useState(initial?.study_date ?? todayIso());
  const [comparison, setComparison] = useState(initial?.comparison_date ?? "");
  // Verbatim: never trimmed or rewritten.
  const [impression, setImpression] = useState(initial?.impression ?? "");
  const [findings, setFindings] = useState<FindingDraft[]>([{ ...EMPTY_FINDING }]);
  const [error, setError] = useState<string | null>(null);
  const set = (i: number, field: keyof FindingDraft, value: string) => setFindings((all) => all.map((f, j) => (j === i ? { ...f, [field]: value } : f)));
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await onSave({
        modality: modality.trim(), body_region: region.trim() || null, study_date: date, comparison_date: comparison || null,
        impression: impression.trim() ? impression : null,
        findings: withFindings ? findings.map(findingOf).filter((f): f is NewFinding => f !== null) : [],
      });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  return (
    <form aria-label={initial ? `Correct ${scanName(initial)}` : "New scan"} onSubmit={submit} className="flex flex-col gap-3 rounded-md border border-border bg-background p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs font-medium">Modality<input required list="modalities" value={modality} onChange={(e) => setModality(e.target.value)} className={FIELD} /></label>
        <datalist id="modalities">{["CT", "MRI", "PET-CT", "X-ray", "Ultrasound", "Bone scan", "Mammogram"].map((m) => <option key={m} value={m} />)}</datalist>
        <label className="flex flex-col gap-1 text-xs font-medium">Body region<input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="e.g. Chest, abdomen and pelvis" className={FIELD} /></label>
        <label className="flex flex-col gap-1 text-xs font-medium">Date<input type="date" required value={date} onChange={(e) => setDate(e.target.value)} className={FIELD} /></label>
        <label className="flex flex-col gap-1 text-xs font-medium">Compared with<input type="date" value={comparison} onChange={(e) => setComparison(e.target.value)} className={FIELD} /></label>
      </div>
      <label className="flex flex-col gap-1 text-xs font-medium">
        Impression (paste it exactly as reported)
        <textarea value={impression} onChange={(e) => setImpression(e.target.value)} rows={4} className={`${FIELD} h-auto py-1.5`} />
      </label>
      {withFindings && (
        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
          <legend className="mb-1 text-xs font-semibold">Findings</legend>
          {findings.map((f, i) => <FindingInputs key={i} n={i + 1} finding={f} conditions={conditions} set={(field, value) => set(i, field, value)} />)}
          <div><button type="button" onClick={() => setFindings((all) => [...all, { ...EMPTY_FINDING }])} className="text-xs font-medium text-primary">Add a finding</button></div>
        </fieldset>
      )}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">{initial ? "Save" : "Add scan"}</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}
