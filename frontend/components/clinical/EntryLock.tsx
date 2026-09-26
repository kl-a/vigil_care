import { Lock } from "lucide-react";

/** Shown instead of entry buttons to a User whose Job Title can't enter this kind of value (design doc §6.4). */
export function EntryLock({ who = "clinician/coordinator" }: { who?: string }) {
  return <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Lock aria-hidden className="h-3 w-3" />Needs {who}</span>;
}
