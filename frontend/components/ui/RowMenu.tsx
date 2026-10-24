"use client";

import { MoreHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";

/** A row's rare or destructive actions (e.g. Remove) behind "⋯"; the main action stays visible beside it. */
export function RowMenu({ label, items }: { label: string; items: { label: string; onSelect: () => void; danger?: boolean }[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => { if (!ref.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);
  return (
    <span ref={ref} className="relative inline-flex" data-noprint>
      <button aria-label={`More actions: ${label}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}
        className="inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-muted">
        <MoreHorizontal aria-hidden className="h-4 w-4" />
      </button>
      {open && (
        <span role="menu" onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
          className="absolute right-0 top-7 z-20 flex min-w-[140px] flex-col rounded-md border border-border bg-card py-1 shadow-card">
          {items.map((item) => (
            <button key={item.label} role="menuitem" onClick={() => { setOpen(false); item.onSelect(); }}
              className={`px-3 py-1.5 text-left text-[13px] hover:bg-muted ${item.danger ? "text-neg" : ""}`}>
              {item.label}
            </button>
          ))}
        </span>
      )}
    </span>
  );
}
