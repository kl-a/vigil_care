/**
 * Second-level tabs (e.g. Clinical Data's): segmented buttons, each with an optional count, clearly below the
 * Patient tabs above them (frontend-design §7).
 */
export function SubTabs<K extends string>({ label, tabs, current, onChange }: {
  label: string; tabs: readonly { key: K; label: string; count?: number | null }[]; current: K; onChange: (key: K) => void;
}) {
  return (
    <nav aria-label={label} className="flex flex-wrap gap-1.5">
      {tabs.map((tab) => (
        <button key={tab.key} onClick={() => onChange(tab.key)} aria-current={current === tab.key ? "page" : undefined}
          aria-label={tab.count !== undefined && tab.count !== null ? `${tab.label} ${tab.count}` : undefined}
          className={`inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-[13px] font-medium ${
            current === tab.key ? "border-primary/40 bg-accent text-primary" : "border-border bg-card text-foreground hover:bg-muted"
          }`}>
          {tab.label}
          {tab.count !== undefined && tab.count !== null && <span className="text-xs font-normal text-muted-foreground">{tab.count}</span>}
        </button>
      ))}
    </nav>
  );
}
