import type { ReactNode } from "react";

/** Semantic state colours (docs/frontend-design.md §4.1): good, caution, bad, neutral. */
export type Tone = "pos" | "cau" | "neg" | "neu";

const TONE: Record<Tone, string> = {
  pos: "border-pos-bd bg-pos-bg text-pos",
  cau: "border-cau-bd bg-cau-bg text-cau",
  neg: "border-neg-bd bg-neg-bg text-neg",
  neu: "border-neu-bd bg-neu-bg text-neu",
};

export function StatusPill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`w-fit rounded-full border px-2 py-0.5 text-xs font-medium ${TONE[tone]}`}>{children}</span>;
}
