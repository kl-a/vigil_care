import { ArrowDown, ArrowUp, CircleCheck, TriangleAlert, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { LabFlag } from "@/lib/clinical";

/** A value nobody has recorded: italic "Not recorded" (never blank, never hidden). */
export function NotRecorded({ children = "Not recorded" }: { children?: ReactNode }) {
  return <em className="text-muted-foreground">{children}</em>;
}

/** A value awaiting review (Extracted Facts, from Stage 9): dotted underline in the caution colour. */
export function Pending({ children }: { children: ReactNode }) {
  return <span title="Pending review" className="underline decoration-cau decoration-dotted underline-offset-4">{children}</span>;
}

const FLAG: Partial<Record<LabFlag, { word: string; icon: LucideIcon; tone: string }>> = {
  low: { word: "Low", icon: ArrowDown, tone: "text-neg" },
  high: { word: "High", icon: ArrowUp, tone: "text-neg" },
  critical: { word: "Critical", icon: TriangleAlert, tone: "text-neg" },
};

/** Outside the reference range: arrow and word ("↑ High"), in the flag colour. Nothing for a normal result. */
export function FlagWord({ flag }: { flag: LabFlag | null | undefined }) {
  const mark = flag ? FLAG[flag] : undefined;
  if (!mark) return null;
  const Icon = mark.icon;
  return <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${mark.tone}`}><Icon aria-hidden className="h-3 w-3" />{mark.word}</span>;
}

/** What the value styles on a page mean. */
export function ValueLegend({ pending = false }: { pending?: boolean }) {
  return (
    <p aria-label="Legend" className="m-0 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      <span className="inline-flex items-center gap-1"><CircleCheck aria-hidden className="h-3.5 w-3.5 text-pos" />Verified</span>
      {pending && <span><Pending>value</Pending> Pending review</span>}
      <span className="inline-flex items-center gap-1"><ArrowUp aria-hidden className="h-3 w-3 text-neg" />Outside reference range</span>
      <span><NotRecorded /> = missing</span>
    </p>
  );
}
