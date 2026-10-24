import type { ReactNode } from "react";

/**
 * A table in a card, with its toolbar inside (frontend-design §7): search and filters on the left, the row count
 * on the right, then the table.
 */
export function TableCard({ label, toolbar, count, children }: { label: string; toolbar?: ReactNode; count?: string; children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-md border border-border bg-card">
      {(toolbar || count) && (
        <div role="toolbar" aria-label={`${label} filters`} className="flex flex-wrap items-center gap-3 border-b border-border px-3 py-2.5">
          {toolbar}
          {count && <span className="ml-auto text-xs text-muted-foreground">{count}</span>}
        </div>
      )}
      <div className="overflow-x-auto">{children}</div>
    </div>
  );
}
