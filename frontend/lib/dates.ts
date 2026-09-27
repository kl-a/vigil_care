/** Clinical dates are written one way everywhere (lib/format). */
export { formatDate } from "./format";

/** Today in the browser's calendar, as the API's ISO date. */
export function todayIso(now: Date = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
