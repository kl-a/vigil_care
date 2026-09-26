import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({ search: "", replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/pbs",
  useSearchParams: () => new URLSearchParams(nav.search),
  useRouter: () => ({ replace: nav.replace, push: vi.fn() }),
  notFound: vi.fn(),
}));

const pbs = vi.hoisted(() => ({ fetchPbsSchedule: vi.fn(), fetchPbsFilters: vi.fn(), listPbsDrugs: vi.fn(), fetchPbsDrug: vi.fn() }));
vi.mock("@/lib/pbs", async (importOriginal) => ({ ...(await importOriginal<object>()), ...pbs }));

import PbsPage from "@/app/(app)/pbs/page";
import PbsDrugPage from "@/app/(app)/pbs/[itemCode]/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { canAccess } from "@/lib/navigation";
import { backHref, byPrescribingRules, drugHref, listQueryOf, maximumOf, NO_FILTERS, type PbsDrug, type PbsDrugRow, type PbsItemView, type PbsScheduleStatus } from "@/lib/pbs";
import { userWith } from "./fixtures";

const REFRESH = { status: "succeeded", source: "pbs_api", refreshed_at: "2026-09-02T01:00:00Z", schedule_date: "2026-09-01" };
const STATUS: PbsScheduleStatus = {
  schedule_date: "2026-09-01", is_sample: false, item_count: 6966, safety_net_general: 1748.2, safety_net_concessional: 277.2,
  current: REFRESH, last_refresh: REFRESH,
};
const NERVOUS = { code: "N", label: "Nervous system" };
const ANTINEOPLASTIC = { code: "L", label: "Antineoplastic and immunomodulating agents" };

const MELANOMA = {
  indication: "Stage IIIB, Stage IIIC or Stage IIID malignant melanoma", treatment_phase: "Initial treatment - 3 weekly treatment regimen",
  level: "authority_required", restriction_code: "14771_14770_R", conditions: ["The treatment must be in addition to complete surgical resection; AND"],
};

const item = (overrides: Partial<PbsItemView>): PbsItemView => ({
  item_code: "12120X", form: "pembrolizumab 100 mg/4 mL injection, 4 mL vial", program_code: "IN",
  program_title: "Section 100 (Efficient Funding of Chemotherapy) - Private Hospitals", atc_codes: ["L01FF02"], brand_names: ["Keytruda"],
  restriction_level: "authority_required", max_quantity: null, max_packs: null, pack_size: null, max_amount: 200, amount_unit: "mg", repeats: 7,
  copay_general: 25, copay_concessional: 7.7, schedule_date: "2026-09-01", listings: [MELANOMA],
  ...overrides,
});

const PEMBROLIZUMAB: PbsDrug = {
  drug_name: "Pembrolizumab", brand_names: ["Keytruda"], groups: [ANTINEOPLASTIC], schedule_date: "2026-09-01",
  items: [
    item({}),
    item({ item_code: "12127G", program_code: "IP", program_title: "Section 100 (Efficient Funding of Chemotherapy) - Public Hospitals" }),
    item({
      item_code: "13739D", max_amount: 400,
      listings: [{ indication: "Stage II or Stage III triple negative breast cancer", treatment_phase: null, level: "authority_required_streamlined", restriction_code: "x_R", conditions: [] }],
    }),
  ],
};

const DEXAMFETAMINE_ROW: PbsDrugRow = {
  drug_name: "Dexamfetamine", brand_names: ["Aspen Dexamfetamine"], item_code: "1165H", item_count: 1,
  forms: ["dexamfetamine sulfate 5 mg tablet, 100"], groups: [NERVOUS], levels: ["authority_required"],
};
const PEMBROLIZUMAB_ROW: PbsDrugRow = {
  drug_name: "Pembrolizumab", brand_names: ["Keytruda"], item_code: "12120X", item_count: 14,
  forms: ["pembrolizumab 100 mg/4 mL injection, 4 mL vial", "pembrolizumab 50 mg injection", "pembrolizumab 25 mg/mL"],
  groups: [ANTINEOPLASTIC], levels: ["authority_required", "authority_required_streamlined"],
};

function renderAs(ui: React.ReactNode) {
  render(<ViewerProvider initialUser={userWith("clinician")}>{ui}</ViewerProvider>);
}

describe("PBS Drug Lookup", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    nav.search = "";
    pbs.fetchPbsSchedule.mockResolvedValue(STATUS);
    pbs.fetchPbsFilters.mockResolvedValue({
      groups: [{ code: "cancer", label: "Cancer drugs (ATC L01, L02)" }, ANTINEOPLASTIC, NERVOUS],
      programs: [{ code: "GE", label: "General Schedule" }],
    });
    pbs.listPbsDrugs.mockResolvedValue({ drugs: [DEXAMFETAMINE_ROW, PEMBROLIZUMAB_ROW], total: 812, page: 1, page_size: 50 });
    pbs.fetchPbsDrug.mockResolvedValue(PEMBROLIZUMAB);
  });

  it("opens on every drug, A–Z, each row saying what it shows", async () => {
    renderAs(<PbsPage />);
    expect(await screen.findByText("812 drugs · page 1 of 17")).toBeInTheDocument();
    expect(pbs.listPbsDrugs).toHaveBeenCalledWith(NO_FILTERS);
    const table = screen.getByRole("table", { name: "Drugs" });
    for (const header of ["Drug (active ingredient) and brands", "Forms and strengths", "Therapeutic group", "Listing types"]) {
      expect(within(table).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    const row = within(table).getByRole("link", { name: "Dexamfetamine" }).closest("tr")!;
    expect(row).toHaveTextContent("Aspen Dexamfetamine");
    expect(row).toHaveTextContent("dexamfetamine sulfate 5 mg tablet, 100");
    expect(row).toHaveTextContent("Nervous system");
    expect(within(row).getByText("Authority Required")).toHaveClass("text-cau");
    const pembro = within(table).getByRole("link", { name: "Pembrolizumab" }).closest("tr")!;
    expect(pembro).toHaveTextContent("and 1 more · 14 PBS Items");
    expect(pembro).toHaveTextContent("Authority Required (Streamlined)");
  });

  it("reads its search, filters and page from the address, and links each drug back to this list", async () => {
    nav.search = "q=dex&group=N&level=authority_required&page=2";
    renderAs(<PbsPage />);
    const expected = { q: "dex", group: "N", program: "", level: "authority_required", page: 2 };
    await waitFor(() => expect(pbs.listPbsDrugs).toHaveBeenCalledWith(expected));
    expect(screen.getByLabelText("Drug, brand or item code")).toHaveValue("dex");
    await waitFor(() => expect(screen.getByLabelText("Therapeutic group")).toHaveValue("N"));
    expect(screen.getByLabelText("Listing type")).toHaveValue("authority_required");
    expect(await screen.findByRole("link", { name: "Dexamfetamine" })).toHaveAttribute("href", drugHref("1165H", expected));
  });

  it("puts a filter change in the address, back on page 1", async () => {
    nav.search = "page=3";
    renderAs(<PbsPage />);
    await screen.findByText("812 drugs · page 1 of 17");
    await waitFor(() => expect(screen.getByRole("option", { name: "Nervous system" })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Therapeutic group"), { target: { value: "N" } });
    expect(nav.replace).toHaveBeenLastCalledWith("/pbs?group=N", { scroll: false });
    fireEvent.change(screen.getByLabelText("PBS program"), { target: { value: "GE" } });
    expect(nav.replace).toHaveBeenLastCalledWith("/pbs?program=GE", { scroll: false });
  });

  it("searches after a pause in typing, through the address", async () => {
    renderAs(<PbsPage />);
    fireEvent.change(await screen.findByLabelText("Drug, brand or item code"), { target: { value: "dexamfetamine" } });
    await waitFor(() => expect(nav.replace).toHaveBeenLastCalledWith("/pbs?q=dexamfetamine", { scroll: false }));
  });

  it("pages through the list", async () => {
    renderAs(<PbsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Next →" }));
    expect(nav.replace).toHaveBeenLastCalledWith("/pbs?page=2", { scroll: false });
    expect(screen.getByRole("button", { name: "← Previous" })).toBeDisabled();
  });

  it("says when nothing matches", async () => {
    pbs.listPbsDrugs.mockResolvedValue({ drugs: [], total: 0, page: 1, page_size: 50 });
    nav.search = "q=zzz";
    renderAs(<PbsPage />);
    expect(await screen.findByText("No drugs in the PBS Schedule match.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(nav.replace).toHaveBeenLastCalledWith("/pbs", { scroll: false });
  });

  it("says which schedule it shows", async () => {
    renderAs(<PbsPage />);
    expect(await screen.findByText(/PBS Schedule of 1 Sep 2026, loaded/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("warns that the Sample Schedule is out of date and for demos only", async () => {
    pbs.fetchPbsSchedule.mockResolvedValue({ ...STATUS, is_sample: true, current: { ...REFRESH, status: "partial", source: "sample" } });
    renderAs(<PbsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Sample data from the PBS Schedule of 1 Sep 2026: out of date, for demos only. Don't use it for clinical decisions.",
    );
  });

  it("warns when the last Refresh failed, and still shows the previous schedule", async () => {
    pbs.fetchPbsSchedule.mockResolvedValue({ ...STATUS, last_refresh: { ...REFRESH, status: "failed", refreshed_at: "2026-10-01T01:00:00Z" } });
    renderAs(<PbsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The last PBS Refresh failed");
    expect(screen.getByText(/PBS Schedule of 1 Sep 2026, loaded/)).toBeInTheDocument();
  });

  it("says when no schedule has been loaded", async () => {
    pbs.fetchPbsSchedule.mockResolvedValue({ ...STATUS, schedule_date: null, item_count: 0, current: null, last_refresh: null });
    renderAs(<PbsPage />);
    expect(await screen.findByText(/No PBS Schedule has been loaded yet/)).toBeInTheDocument();
  });

  it("goes back to the list the drug was opened from", async () => {
    nav.search = `back=${encodeURIComponent("q=dex&group=N&page=2")}`;
    renderAs(<PbsDrugPage params={{ itemCode: "12120X" }} />);
    expect(await screen.findByRole("link", { name: "← Back to results" })).toHaveAttribute("href", "/pbs?q=dex&group=N&page=2");
  });

  it("shows a drug in labelled sections: its PBS Items, when it can be prescribed, and what the patient pays", async () => {
    renderAs(<PbsDrugPage params={{ itemCode: "12120X" }} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Pembrolizumab" })).toBeInTheDocument();
    expect(pbs.fetchPbsDrug).toHaveBeenCalledWith("12120X");
    expect(screen.getByText("Antineoplastic and immunomodulating agents")).toBeInTheDocument();

    const overview = screen.getByRole("table", { name: "PBS Items" });
    for (const header of ["Item code", "Form and strength", "PBS program", "Maximum per prescription", "Repeats", "Listing types"]) {
      expect(within(overview).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    const first = within(overview).getByText("12120X").closest("tr")!;
    expect(within(first).getByText("12120X")).toHaveClass("font-mono");
    expect(first).toHaveTextContent("Section 100 (Efficient Funding of Chemotherapy) - Private Hospitals");
    expect(first).toHaveTextContent("200 mg");

    // 12120X and 12127G share their restrictions: shown once.
    const shared = screen.getByRole("region", { name: "When it can be prescribed: PBS Items 12120X, 12127G" });
    const melanoma = within(shared).getByText(MELANOMA.indication).closest("tr")!;
    expect(melanoma).toHaveTextContent("Initial treatment - 3 weekly treatment regimen");
    expect(within(melanoma).getByText("Authority Required")).toHaveClass("text-cau");
    expect(melanoma).toHaveTextContent("The treatment must be in addition to complete surgical resection; AND");
    const tnbc = screen.getByRole("region", { name: "When it can be prescribed: PBS Item 13739D" });
    expect(tnbc).toHaveTextContent("Authority Required (Streamlined)");

    const pays = screen.getByRole("region", { name: "What the patient pays" });
    expect(pays).toHaveTextContent("Up to $25.00 per prescription");
    expect(pays).toHaveTextContent("Up to $7.70 per prescription");
    await waitFor(() => expect(pays).toHaveTextContent("$1,748.20 general, $277.20 concessional"));
    expect(screen.getAllByText(/Up to \$25\.00/)).toHaveLength(1);
  });

  it("shows an Unrestricted item as listed for any indication", async () => {
    pbs.fetchPbsDrug.mockResolvedValue({
      drug_name: "Carboplatin", brand_names: ["Carboplatin Accord"], groups: [ANTINEOPLASTIC], schedule_date: "2026-09-01",
      items: [item({ item_code: "10150F", restriction_level: "unrestricted", listings: [] })],
    });
    renderAs(<PbsDrugPage params={{ itemCode: "10150F" }} />);
    const row = (await screen.findByText("Any indication")).closest("tr")!;
    expect(within(row).getByText("Unrestricted")).toHaveClass("text-pos");
  });

  it("explains an item that isn't in the current schedule", async () => {
    pbs.fetchPbsDrug.mockRejectedValue(new Error("No such item in the current PBS Schedule."));
    renderAs(<PbsDrugPage params={{ itemCode: "99999Z" }} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No such item in the current PBS Schedule.");
  });

  it("is for clinicians, trial coordinators and secretaries, not developer admins", () => {
    expect(canAccess("/pbs/12120X", "secretary")).toBe(true);
    expect(canAccess("/pbs", "trial_coordinator")).toBe(true);
    expect(canAccess("/pbs/12120X", "developer_admin")).toBe(false);
  });
});

describe("PBS list state and quantities", () => {
  it("round-trips the list's state, and only ever goes back to the PBS list", () => {
    const query = { q: "dex", group: "N", program: "GE", level: "restricted", page: 3 };
    expect(listQueryOf(new URLSearchParams("q=dex&group=N&program=GE&level=restricted&page=3"))).toEqual(query);
    expect(listQueryOf(new URLSearchParams("page=-2"))).toEqual(NO_FILTERS);
    expect(backHref(new URLSearchParams(drugHref("1165H", query).split("?")[1]).get("back"))).toBe(
      "/pbs?q=dex&group=N&program=GE&level=restricted&page=3",
    );
    expect(drugHref("1165H", NO_FILTERS)).toBe("/pbs/1165H");
    expect(backHref(null)).toBe("/pbs");
    expect(backHref("https://evil.example/?q=x")).toBe("/pbs");
  });

  it("gives every maximum a unit", () => {
    const none = { max_amount: null, amount_unit: null, max_quantity: null, max_packs: null, pack_size: null };
    expect(maximumOf({ ...none, max_amount: 200, amount_unit: "mg" })).toBe("200 mg");
    expect(maximumOf({ ...none, max_quantity: 100, max_packs: 1, pack_size: 100 })).toBe("100 (1 pack of 100)");
    expect(maximumOf({ ...none, max_quantity: 56, max_packs: 2, pack_size: 28 })).toBe("56 (2 packs of 28)");
    expect(maximumOf(none)).toBe("—");
  });

  it("groups items that share the same prescribing rules", () => {
    expect(byPrescribingRules(PEMBROLIZUMAB.items).map((rules) => rules.items.map((i) => i.item_code))).toEqual([["12120X", "12127G"], ["13739D"]]);
  });
});
