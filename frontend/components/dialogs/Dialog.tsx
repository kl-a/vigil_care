"use client";

import { useId, useState, type ReactNode } from "react";
import { messageOf } from "@/lib/api";

export function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const titleId = useId();
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4" onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <div role="dialog" aria-modal="true" aria-labelledby={titleId} className="flex w-full max-w-[440px] flex-col gap-3 rounded-md border border-border bg-card p-5 shadow-card">
        <h2 id={titleId} className="m-0 text-base font-semibold">{title}</h2>
        {children}
      </div>
    </div>
  );
}

/** Runs a confirm action, keeping the dialog open with the backend's explanation if it's refused. */
export function useConfirm(action: () => Promise<void>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function confirm() {
    setBusy(true);
    setError(null);
    try { await action(); } catch (reason) { setError(messageOf(reason)); setBusy(false); }
  }
  return { busy, error, confirm };
}

export function DialogActions({ onCancel, confirmLabel, disabled, danger, onConfirm }: {
  onCancel: () => void; confirmLabel: string; disabled: boolean; danger?: boolean; onConfirm: () => void;
}) {
  return (
    <div className="flex justify-end gap-2">
      <button onClick={onCancel} className="h-8 rounded-md border border-border px-3 text-[13px]">Cancel</button>
      <button onClick={onConfirm} disabled={disabled}
        className={`h-8 rounded-md px-3 text-[13px] font-medium disabled:opacity-50 ${danger ? "bg-neg text-white" : "bg-primary text-primary-foreground"}`}>
        {confirmLabel}
      </button>
    </div>
  );
}
