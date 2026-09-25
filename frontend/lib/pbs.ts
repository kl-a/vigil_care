import { request, type Schemas } from "./api";

export type PbsScheduleStatus = Schemas["PbsScheduleStatus"];
export type PbsDrugRow = Schemas["PbsDrugRow"];
export type PbsDrug = Schemas["PbsDrug"];
export type PbsItemView = Schemas["PbsItemView"];
export type PbsListingView = Schemas["PbsListingView"];

export const fetchPbsSchedule = () => request<PbsScheduleStatus>("/pbs/schedule");
export const searchPbs = (q: string) => request<PbsDrugRow[]>(`/pbs/drugs?${new URLSearchParams({ q: q.trim() })}`);
export const fetchPbsDrug = (itemCode: string) => request<PbsDrug>(`/pbs/drugs/${encodeURIComponent(itemCode)}`);

/** PBS Listing for an indication (CONTEXT.md): never "PBS-listed" without one. */
export type PbsListing = "unrestricted" | "restricted" | "authority_required" | "not_listed";

/** A restriction level as its PBS Listing; streamlined authority is still Authority Required. */
export function listingOf(level: string): { listing: PbsListing; streamlined: boolean } {
  if (level === "authority_required_streamlined") return { listing: "authority_required", streamlined: true };
  if (level === "unrestricted" || level === "restricted" || level === "authority_required") return { listing: level, streamlined: false };
  return { listing: "not_listed", streamlined: false };
}

/** Program codes, as the PBS names them; others are shown as their code. */
export const PROGRAM_LABEL: Record<string, string> = {
  GE: "General Schedule",
  IN: "Efficient Funding of Chemotherapy (private hospital)",
  IP: "Efficient Funding of Chemotherapy (public hospital)",
  HS: "Highly Specialised Drugs (private hospital)",
  HB: "Highly Specialised Drugs (public hospital)",
};

/** "$25.00", or "—". */
export function formatMoney(amount: number | null | undefined): string {
  return amount === null || amount === undefined ? "—" : amount.toLocaleString("en-AU", { style: "currency", currency: "AUD" });
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "1 Sep 2026", or "—". */
export function formatScheduleDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [year, month, day] = iso.split("-").map(Number);
  return `${day} ${MONTHS[month! - 1]} ${year}`;
}

/** An item's maximum per prescription: an amount for infusions (e.g. "200 mg"), otherwise a quantity. */
export function maximumOf(item: Pick<PbsItemView, "max_amount" | "amount_unit" | "max_quantity">): string {
  if (item.max_amount !== null && item.max_amount !== undefined) return `${item.max_amount} ${item.amount_unit ?? ""}`.trim();
  return item.max_quantity === null || item.max_quantity === undefined ? "—" : String(item.max_quantity);
}
