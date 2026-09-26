import { StatusPill, type Tone } from "@/components/ui/StatusPill";

/** One System status tile: what it checks, its state, and a line on what that means. */
export function Check({ label, value, tone, detail }: { label: string; value: string; tone: Tone; detail: string }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-border bg-card p-4">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <StatusPill tone={tone}>{value}</StatusPill>
      <span className="text-xs text-muted-foreground">{detail}</span>
    </div>
  );
}
