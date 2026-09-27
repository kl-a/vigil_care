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

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** A clinical date: "18 Sep 2026", or "—". Takes the API's ISO date (a datetime's date part is used as is). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number) as [number, number, number];
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

/** A moment, in the viewer's time: "18 Sep 2026, 13:20" (24-hour), or "Never". */
export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "Never";
  const at = new Date(iso);
  return `${at.getDate()} ${MONTHS[at.getMonth()]} ${at.getFullYear()}, ${formatTime(at)}`;
}

/** A time of day: "13:20". */
export function formatTime(at: Date): string {
  return `${String(at.getHours()).padStart(2, "0")}:${String(at.getMinutes()).padStart(2, "0")}`;
}
