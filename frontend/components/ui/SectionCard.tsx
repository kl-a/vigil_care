import type { ReactNode } from "react";

/**
 * A titled card (frontend-design §7): the title on the left, a quiet meta line on the right (e.g. "Updated
 * 14 Sep 2026 ✓", the source), and an optional action. The one card every section uses.
 */
export function SectionCard({ id, title, meta, action, children, className = "" }: {
  id: string; title: ReactNode; meta?: ReactNode; action?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section aria-labelledby={id} className={`flex break-inside-avoid flex-col rounded-md border border-border bg-card ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-2.5">
        <h2 id={id} className="m-0 text-sm font-semibold">{title}</h2>
        {(meta || action) && (
          <span className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">{meta}{action}</span>
        )}
      </div>
      <div className="flex flex-col gap-2 p-4">{children}</div>
    </section>
  );
}
