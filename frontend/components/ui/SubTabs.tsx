/**
 * Second-level tabs (e.g. Clinical Data's): segmented buttons, each with an optional count, clearly below the
 * Patient tabs above them (frontend-design §7). The selected one is a state, not an action: neutral, never the
 * primary colour (§4.1).
 */
export function SubTabs<K extends string>({ label, tabs, current, onChange }: {
  label: string; tabs: readonly { key: K; label: string; count?: number | null }[]; current: K; onChange: (key: K) => void;
}) {
  return (
    <nav aria-label={label} className="flex flex-wrap gap-1.5">
      {tabs.map((tab) => (
        <button key={tab.key} onClick={() => onChange(tab.key)} aria-current={current === tab.key ? "page" : undefined}
          aria-label={tab.count !== undefined && tab.count !== null ? `${tab.label} ${tab.count}` : undefined}
          className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2.5 text-xs font-medium ${
            current === tab.key ? "border-foreground/40 bg-muted text-foreground font-semibold" : "border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}>
          {tab.label}
          {tab.count !== undefined && tab.count !== null && <span className="text-xs font-normal text-muted-foreground">{tab.count}</span>}
        </button>
      ))}
    </nav>
  );
}
