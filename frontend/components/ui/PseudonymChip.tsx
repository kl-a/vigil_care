/** The Patient's Pseudonym, in the privacy tone: what De-identified Exports carry instead of their identity. */
export function PseudonymChip({ pseudonym }: { pseudonym: string }) {
  return (
    <span title="Pseudonym: printed only on De-identified Exports"
      className="inline-flex items-center rounded border border-pri-bd bg-pri-bg px-1.5 font-mono text-[11px] font-medium text-pri">
      {pseudonym}
    </span>
  );
}
