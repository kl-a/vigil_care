/** How Vigil writes clinical values (docs/frontend-design.md): one place, so every screen agrees. */

const SUPERSCRIPT: Record<string, string> = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "-": "⁻" };

/** A unit as printed on a report: "x10^9/L" becomes "×10⁹/L". */
export function formatUnit(unit: string | null | undefined): string {
  if (!unit) return "";
  return unit
    .replace(/^x(?=10\^)/, "×")
    .replace(/\^(-?\d+)/g, (_, power: string) => [...power].map((c) => SUPERSCRIPT[c] ?? c).join(""));
}

/** A reference range. One-sided ranges read as the flag does (a value above the high end is High): "≤20", "≥60". */
export function formatRange(low: string | number | null | undefined, high: string | number | null | undefined): string {
  const has = (v: unknown) => v !== null && v !== undefined && v !== "";
  if (has(low) && has(high)) return `${low}–${high}`;
  if (has(high)) return `≤${high}`;
  if (has(low)) return `≥${low}`;
  return "—";
}
