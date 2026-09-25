"use client";

import { useState, type ReactNode } from "react";
import { Dialog, DialogActions, useConfirm } from "./Dialog";

/**
 * SignOffDialog (docs/frontend-design.md §7): the User confirms, with a checkbox, that the change is signed
 * off in their name. It is recorded as a Verification with their name, Job Title and the time.
 */
export function SignOffDialog({ title, actor, confirmLabel, canConfirm = true, onConfirm, onClose, children }: {
  title: string;
  /** "Name (Job Title)" of the User signing off. */
  actor: string;
  confirmLabel: string;
  canConfirm?: boolean;
  onConfirm: () => Promise<void>;
  onClose: () => void;
  children?: ReactNode;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const { busy, error, confirm } = useConfirm(onConfirm);
  return (
    <Dialog title={title} onClose={onClose}>
      {children}
      <label className="flex items-start gap-2 rounded-md border border-border bg-muted p-2 text-xs">
        <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="mt-0.5" />
        <span>I confirm this change. Sign it off as <strong>{actor}</strong>.</span>
      </label>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <DialogActions onCancel={onClose} confirmLabel={confirmLabel} disabled={busy || !confirmed || !canConfirm} onConfirm={confirm} />
    </Dialog>
  );
}
