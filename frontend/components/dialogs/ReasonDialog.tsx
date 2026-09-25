"use client";

import { useState, type ReactNode } from "react";
import { FIELD } from "@/components/ui/styles";
import { Dialog, DialogActions, useConfirm } from "./Dialog";

/**
 * ReasonDialog (docs/frontend-design.md §7): an action that must say why (deactivate, soft delete, hold).
 * The reason is recorded on the Verification.
 */
export function ReasonDialog({ title, actor, confirmLabel, reasonRequired = true, danger, onConfirm, onClose, children }: {
  title: string;
  actor: string;
  confirmLabel: string;
  reasonRequired?: boolean;
  danger?: boolean;
  onConfirm: (reason: string | undefined) => Promise<void>;
  onClose: () => void;
  children?: ReactNode;
}) {
  const [reason, setReason] = useState("");
  const trimmed = reason.trim();
  const { busy, error, confirm } = useConfirm(() => onConfirm(trimmed || undefined));
  return (
    <Dialog title={title} onClose={onClose}>
      {children}
      <label className="flex flex-col gap-1 text-xs font-medium">
        {reasonRequired ? "Reason (required)" : "Reason (optional)"}
        <input id="reason-dialog-reason" value={reason} onChange={(e) => setReason(e.target.value)} className={FIELD} />
      </label>
      <p className="m-0 text-xs text-muted-foreground">Recorded in the audit trail as a sign-off by {actor}.</p>
      {error && <p role="alert" className="m-0 text-[13px] text-neg">{error}</p>}
      <DialogActions onCancel={onClose} confirmLabel={confirmLabel} danger={danger} disabled={busy || (reasonRequired && !trimmed)} onConfirm={confirm} />
    </Dialog>
  );
}
