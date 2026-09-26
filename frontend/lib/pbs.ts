import { request, type Schemas } from "./api";

export type PbsScheduleStatus = Schemas["PbsScheduleStatus"];
export type PbsDrugRow = Schemas["PbsDrugRow"];
export type PbsDrugPage = Schemas["PbsDrugPage"];
export type PbsFilters = Schemas["PbsFilters"];
export type PbsOption = Schemas["PbsOption"];
export type PbsDrug = Schemas["PbsDrug"];
export type PbsItemView = Schemas["PbsItemView"];
export type PbsListingView = Schemas["PbsListingView"];

/** The drug list's search, filters and page: kept in the page address so going back returns to the same list. */
export type PbsListQuery = { q: string; group: string; program: string; level: string; page: number };
export const NO_FILTERS: PbsListQuery = { q: "", group: "", program: "", level: "", page: 1 };

export function listQueryOf(params: URLSearchParams): PbsListQuery {
  const page = Number(params.get("page"));
  return {
    q: params.get("q") ?? "",
    group: params.get("group") ?? "",
    program: params.get("program") ?? "",
    level: params.get("level") ?? "",
    page: Number.isInteger(page) && page > 1 ? page : 1,
  };
}

/** The query as URL search params, leaving out what's unset (so no filters is just "/pbs"). */
export function searchParamsOf(query: PbsListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q.trim()) params.set("q", query.q.trim());
  if (query.group) params.set("group", query.group);
  if (query.program) params.set("program", query.program);
  if (query.level) params.set("level", query.level);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

export const fetchPbsSchedule = () => request<PbsScheduleStatus>("/pbs/schedule");
export const fetchPbsFilters = () => request<PbsFilters>("/pbs/filters");
export const listPbsDrugs = (query: PbsListQuery) => request<PbsDrugPage>(`/pbs/drugs?${searchParamsOf(query)}`);
export const fetchPbsDrug = (itemCode: string) => request<PbsDrug>(`/pbs/drugs/${encodeURIComponent(itemCode)}`);

/** A drug's page, remembering the list it was opened from. */
export function drugHref(itemCode: string, from: PbsListQuery): string {
  const back = searchParamsOf(from).toString();
  return `/pbs/${encodeURIComponent(itemCode)}${back ? `?${new URLSearchParams({ back })}` : ""}`;
}

/** Back to the list a drug was opened from: only ever the PBS list, whatever `back` holds. */
export function backHref(back: string | null): string {
  const query = searchParamsOf(listQueryOf(new URLSearchParams(back ?? ""))).toString();
  return query ? `/pbs?${query}` : "/pbs";
}

/** PBS Listing for an indication (CONTEXT.md): never "PBS-listed" without one. */
export type PbsListing = "unrestricted" | "restricted" | "authority_required" | "not_listed";

/** A restriction level as its PBS Listing; Streamlined is still Authority Required. */
export function listingOf(level: string): { listing: PbsListing; streamlined: boolean } {
  if (level === "authority_required_streamlined") return { listing: "authority_required", streamlined: true };
  if (level === "unrestricted" || level === "restricted" || level === "authority_required") return { listing: level, streamlined: false };
  return { listing: "not_listed", streamlined: false };
}

/** The listing types a drug can be filtered by, least restrictive first. */
export const LEVELS: { code: string; label: string }[] = [
  { code: "unrestricted", label: "Unrestricted" },
  { code: "restricted", label: "Restricted" },
  { code: "authority_required", label: "Authority Required" },
  { code: "authority_required_streamlined", label: "Authority Required (Streamlined)" },
];

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

type Quantities = Pick<PbsItemView, "max_amount" | "amount_unit" | "max_quantity" | "max_packs" | "pack_size">;

/**
 * An item's maximum per prescription, with its unit: an amount for infusions ("200 mg"), otherwise units and
 * packs ("100 (1 pack of 100)").
 */
export function maximumOf(item: Quantities): string {
  if (item.max_amount !== null && item.max_amount !== undefined) return `${item.max_amount} ${item.amount_unit ?? ""}`.trim();
  const packs = item.max_packs ? `${item.max_packs} ${item.max_packs === 1 ? "pack" : "packs"}${item.pack_size ? ` of ${item.pack_size}` : ""}` : null;
  if (item.max_quantity === null || item.max_quantity === undefined) return packs ?? "—";
  return packs ? `${item.max_quantity} (${packs})` : String(item.max_quantity);
}

/** Every listing type of an item: its own and its indications', least restrictive first. */
export function levelsOf(item: Pick<PbsItemView, "restriction_level" | "listings">): string[] {
  const found = new Set([item.restriction_level, ...item.listings.map((listing) => listing.level)]);
  return LEVELS.map((level) => level.code).filter((code) => found.has(code));
}

/** Items that share exactly the same restrictions, so each set of prescribing rules is shown once. */
export function byPrescribingRules(items: PbsItemView[]): { items: PbsItemView[]; listings: PbsListingView[] }[] {
  const groups = new Map<string, { items: PbsItemView[]; listings: PbsListingView[] }>();
  for (const item of items) {
    const key = item.listings.length
      ? item.listings.map((listing) => `${listing.restriction_code}:${listing.level}`).join("|")
      : `any:${item.restriction_level}`;
    const group = groups.get(key) ?? { items: [], listings: item.listings };
    group.items.push(item);
    groups.set(key, group);
  }
  return [...groups.values()];
}
