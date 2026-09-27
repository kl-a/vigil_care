"use client";

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { EntryLock } from "@/components/clinical/EntryLock";
import { ReasonDialog } from "@/components/dialogs/ReasonDialog";
import { useSignedInUser } from "@/components/shell/ViewerProvider";
import { StatusPill } from "@/components/ui/StatusPill";
import { FIELD } from "@/components/ui/styles";
import { messageOf } from "@/lib/api";
import {
  addClinicalNote, addManagementPlan, addNextStep, fetchClinicalNotes, fetchEntryRights, fetchManagementPlans, fetchNextSteps,
  markNextStepDone, NEXT_STEP_KIND_LABEL, NOTE_TYPE_LABEL, removeClinicalNote, removeNextStep,
  type ClinicalNoteRow, type ManagementPlanRow, type NextStepKind, type NextStepRow, type NoteType,
} from "@/lib/clinical";
import { formatDate, todayIso } from "@/lib/dates";
import { signOffName } from "@/lib/jobTitles";
import { listProviders, type ProviderRow } from "@/lib/providers";
import { formatWhen } from "@/lib/users";

const BUTTON = "h-7 rounded-md border border-border px-2 text-xs font-medium hover:bg-muted";
const LOCK = <EntryLock />;

function Section({ id, title, action, children }: { id: string; title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id={id} className="m-0 text-sm font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function useProviders(): ProviderRow[] {
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  useEffect(() => { listProviders().then(setProviders).catch(() => setProviders([])); }, []);
  return providers;
}

function ProviderSelect({ label, value, onChange, providers }: { label: string; value: string; onChange: (id: string) => void; providers: ProviderRow[] }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} className={`${FIELD} w-56`}>
        <option value="">Not recorded</option>
        {providers.map((p) => <option key={p.id} value={p.id}>{p.display_name}</option>)}
      </select>
    </label>
  );
}

/** Plan & notes (#45, design doc §5 screen 9): the Management Plan quoted verbatim, Next Steps, and Clinical Notes. */
export function PlanAndNotes({ patientId }: { patientId: string }) {
  const [rights, setRights] = useState<Record<string, boolean>>({});
  useEffect(() => { fetchEntryRights().then(setRights).catch(() => setRights({})); }, []);
  return (
    <div className="flex flex-col gap-4">
      <ManagementPlan patientId={patientId} canEnter={Boolean(rights.management_plan)} />
      <NextSteps patientId={patientId} />
      <ClinicalNotes patientId={patientId} canEnter={Boolean(rights.clinical_note)} />
    </div>
  );
}

function ManagementPlan({ patientId, canEnter }: { patientId: string; canEnter: boolean }) {
  const providers = useProviders();
  const [plans, setPlans] = useState<ManagementPlanRow[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { fetchManagementPlans(patientId).then(setPlans).catch((reason: unknown) => setError(messageOf(reason))); }, [patientId]);
  useEffect(load, [load]);
  const [current, ...earlier] = plans ?? [];
  return (
    <Section id="management-plan" title="Management Plan" action={canEnter ? !adding && <button onClick={() => setAdding(true)} className={BUTTON}>Record new plan</button> : LOCK}>
      {adding && <PlanForm providers={providers} onCancel={() => setAdding(false)} onSave={async (plan) => { await addManagementPlan(patientId, plan); setAdding(false); load(); }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {plans?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {current && <PlanQuote plan={current} />}
      {earlier.length > 0 && (
        <details>
          <summary className="cursor-pointer text-xs text-primary">Earlier plans ({earlier.length})</summary>
          <div className="mt-2 flex flex-col gap-3">{earlier.map((plan) => <PlanQuote key={plan.id} plan={plan} />)}</div>
        </details>
      )}
    </Section>
  );
}

/** Quoted verbatim, exactly as written: Vigil never rewrites it. */
function PlanQuote({ plan }: { plan: ManagementPlanRow }) {
  return (
    <figure className="m-0 flex flex-col gap-1">
      <blockquote className="m-0 whitespace-pre-wrap border-l-2 border-primary pl-3 text-[13px]">{plan.plan_text}</blockquote>
      <figcaption className="text-xs text-muted-foreground">
        {plan.author_name ?? "Author not recorded"}, {formatDate(plan.plan_date)}
        {plan.entered && <> · entered by {plan.entered.by}, {formatWhen(plan.entered.at)}</>}
      </figcaption>
    </figure>
  );
}

function PlanForm({ providers, onCancel, onSave }: {
  providers: ProviderRow[];
  onCancel: () => void;
  onSave: (plan: { plan_text: string; plan_date: string | null; authored_by_provider_id: string | null }) => Promise<void>;
}) {
  const [text, setText] = useState("");
  const [date, setDate] = useState(todayIso());
  const [author, setAuthor] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await onSave({ plan_text: text, plan_date: date || null, authored_by_provider_id: author || null });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  return (
    <form aria-label="New Management Plan" onSubmit={submit} className="flex flex-col gap-3 rounded-md border border-border bg-background p-3">
      <label className="flex flex-col gap-1 text-xs font-medium">
        Plan, exactly as written in the letter
        <textarea required value={text} onChange={(e) => setText(e.target.value)} rows={4} className={`${FIELD} h-auto py-1.5`} />
      </label>
      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium">Date<input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={`${FIELD} w-40`} /></label>
        <ProviderSelect label="Written by" value={author} onChange={setAuthor} providers={providers} />
      </div>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Save plan</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}

function NextSteps({ patientId }: { patientId: string }) {
  const me = useSignedInUser();
  const [steps, setSteps] = useState<NextStepRow[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<NextStepRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { fetchNextSteps(patientId).then(setSteps).catch((reason: unknown) => setError(messageOf(reason))); }, [patientId]);
  useEffect(load, [load]);
  async function done(step: NextStepRow) {
    try { await markNextStepDone(patientId, step.id); load(); } catch (reason) { setError(messageOf(reason)); }
  }
  return (
    <Section id="next-steps" title="Next Steps" action={!adding && <button onClick={() => setAdding(true)} className={BUTTON}>Add Next Step</button>}>
      {adding && <NextStepForm onCancel={() => setAdding(false)} onSave={async (step) => { await addNextStep(patientId, step); setAdding(false); load(); }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {steps?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {steps && steps.length > 0 && (
        <ul aria-label="Next Steps" className="m-0 flex list-none flex-col divide-y divide-border p-0">
          {steps.map((step) => (
            <li key={step.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-[13px]">
              <span className="flex flex-col">
                <span className={step.done ? "text-muted-foreground line-through" : ""}>{step.description}</span>
                <span className="text-xs text-muted-foreground">
                  {NEXT_STEP_KIND_LABEL[step.kind]} · due {formatDate(step.due_date)}
                  {step.done && <> · done by {step.done.by}, {formatWhen(step.done.at)}</>}
                </span>
              </span>
              {!step.done && (
                <span className="inline-flex gap-2">
                  <button onClick={() => done(step)} className="text-xs font-medium text-primary">Mark done</button>
                  <button onClick={() => setRemoving(step)} className="text-xs font-medium text-neg">Remove</button>
                </span>
              )}
              {step.done && <StatusPill tone="pos">Done</StatusPill>}
            </li>
          ))}
        </ul>
      )}
      {removing && (
        <ReasonDialog title={`Remove "${removing.description}"`} actor={signOffName(me)} confirmLabel="Remove Next Step" danger
          onConfirm={async (reason) => { await removeNextStep(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)} />
      )}
    </Section>
  );
}

function NextStepForm({ onCancel, onSave }: { onCancel: () => void; onSave: (step: { kind: NextStepKind; description: string; due_date: string | null }) => Promise<void> }) {
  const [kind, setKind] = useState<NextStepKind>("review");
  const [description, setDescription] = useState("");
  const [due, setDue] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try { await onSave({ kind, description: description.trim(), due_date: due || null }); } catch (reason) { setError(messageOf(reason)); }
  }
  return (
    <form aria-label="New Next Step" onSubmit={submit} className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-background p-3">
      <label className="flex flex-col gap-1 text-xs font-medium">
        Kind
        <select value={kind} onChange={(e) => setKind(e.target.value as NextStepKind)} className={`${FIELD} w-40`}>
          {Object.entries(NEXT_STEP_KIND_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium">What<input required value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Discuss at breast MDT" className={`${FIELD} w-72`} /></label>
      <label className="flex flex-col gap-1 text-xs font-medium">Due<input type="date" value={due} onChange={(e) => setDue(e.target.value)} className={`${FIELD} w-40`} /></label>
      {error && <p role="alert" className="m-0 w-full text-[13px] text-neg">{error}</p>}
      <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Add</button>
      <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
    </form>
  );
}

function ClinicalNotes({ patientId, canEnter }: { patientId: string; canEnter: boolean }) {
  const me = useSignedInUser();
  const providers = useProviders();
  const [notes, setNotes] = useState<ClinicalNoteRow[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<ClinicalNoteRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { fetchClinicalNotes(patientId).then(setNotes).catch((reason: unknown) => setError(messageOf(reason))); }, [patientId]);
  useEffect(load, [load]);
  return (
    <Section id="clinical-notes" title="Clinical Notes and letters" action={canEnter ? !adding && <button onClick={() => setAdding(true)} className={BUTTON}>Add note</button> : LOCK}>
      {adding && <NoteForm providers={providers} onCancel={() => setAdding(false)} onSave={async (note) => { await addClinicalNote(patientId, note); setAdding(false); load(); }} />}
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      {notes?.length === 0 && <p className="m-0 text-[13px] text-muted-foreground">None recorded.</p>}
      {notes && notes.length > 0 && (
        <ul aria-label="Clinical Notes" className="m-0 flex list-none flex-col divide-y divide-border p-0">
          {notes.map((note) => (
            <li key={note.id} className="flex flex-col gap-1 py-2 text-[13px]">
              <span className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium">{NOTE_TYPE_LABEL[note.note_type]} · {formatDate(note.note_date)}</span>
                {canEnter && <button onClick={() => setRemoving(note)} className="text-xs font-medium text-neg">Remove</button>}
              </span>
              <span className="text-xs text-muted-foreground">
                {note.author_name ? `From ${note.author_name}` : "Author not recorded"}{note.recipient_name && ` to ${note.recipient_name}`}
              </span>
              <p className="m-0 whitespace-pre-wrap">{note.content}</p>
            </li>
          ))}
        </ul>
      )}
      {removing && (
        <ReasonDialog title={`Remove this ${NOTE_TYPE_LABEL[removing.note_type].toLowerCase()}`} actor={signOffName(me)} confirmLabel="Remove note" danger
          onConfirm={async (reason) => { await removeClinicalNote(patientId, removing.id, reason ?? ""); setRemoving(null); load(); }}
          onClose={() => setRemoving(null)} />
      )}
    </Section>
  );
}

function NoteForm({ providers, onCancel, onSave }: {
  providers: ProviderRow[];
  onCancel: () => void;
  onSave: (note: { note_type: NoteType; note_date: string | null; author_provider_id: string | null; recipient_provider_id: string | null; content: string }) => Promise<void>;
}) {
  const [type, setType] = useState<NoteType>("clinical_note");
  const [date, setDate] = useState(todayIso());
  const [author, setAuthor] = useState("");
  const [recipient, setRecipient] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await onSave({ note_type: type, note_date: date || null, author_provider_id: author || null, recipient_provider_id: recipient || null, content: content.trim() });
    } catch (reason) {
      setError(messageOf(reason));
    }
  }
  return (
    <form aria-label="New note" onSubmit={submit} className="flex flex-col gap-3 rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Kind
          <select value={type} onChange={(e) => setType(e.target.value as NoteType)} className={`${FIELD} w-48`}>
            {Object.entries(NOTE_TYPE_LABEL).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">Date<input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={`${FIELD} w-40`} /></label>
        <ProviderSelect label="From" value={author} onChange={setAuthor} providers={providers} />
        <ProviderSelect label="To" value={recipient} onChange={setRecipient} providers={providers} />
      </div>
      <label className="flex flex-col gap-1 text-xs font-medium">Note<textarea required value={content} onChange={(e) => setContent(e.target.value)} rows={4} className={`${FIELD} h-auto py-1.5`} /></label>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="h-8 rounded-md bg-primary px-3 text-[13px] font-medium text-primary-foreground">Save note</button>
        <button type="button" onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px] hover:bg-muted">Cancel</button>
      </div>
    </form>
  );
}
