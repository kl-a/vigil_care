import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/pbs", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }), notFound: vi.fn() }));

const pbs = vi.hoisted(() => ({ fetchPbsSchedule: vi.fn(), searchPbs: vi.fn(), fetchPbsDrug: vi.fn() }));
vi.mock("@/lib/pbs", async (importOriginal) => ({ ...(await importOriginal<object>()), ...pbs }));

import PbsPage from "@/app/(app)/pbs/page";
import PbsDrugPage from "@/app/(app)/pbs/[itemCode]/page";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { canAccess } from "@/lib/navigation";
import type { PbsDrug, PbsItemView, PbsScheduleStatus } from "@/lib/pbs";
import { userWith } from "./fixtures";

const REFRESH = { status: "succeeded", source: "pbs_api", refreshed_at: "2026-09-02T01:00:00Z", schedule_date: "2026-09-01" };
const STATUS: PbsScheduleStatus = {
  schedule_date: "2026-09-01", is_sample: false, item_count: 1045, safety_net_general: 1748.2, safety_net_concessional: 277.2,
  current: REFRESH, last_refresh: REFRESH,
};

const item = (overrides: Partial<PbsItemView>): PbsItemView => ({
  item_code: "12120X", form: "pembrolizumab 100 mg/4 mL injection, 4 mL vial", program_code: "IN", brand_names: ["Keytruda"],
  restriction_level: "authority_required", max_quantity: null, max_amount: 200, amount_unit: "mg", repeats: 7,
  copay_general: 25, copay_concessional: 7.7, schedule_date: "2026-09-01",
  listings: [{
    indication: "Stage IIIB, Stage IIIC or Stage IIID malignant melanoma", treatment_phase: "Initial treatment - 3 weekly treatment regimen",
    level: "authority_required", restriction_code: "14771_14770_R", conditions: ["The treatment must be in addition to complete surgical resection; AND"],
  }],
  ...overrides,
});

const PEMBROLIZUMAB: PbsDrug = {
  drug_name: "Pembrolizumab", brand_names: ["Keytruda"], schedule_date: "2026-09-01",
  items: [
    item({}),
    item({
      item_code: "13739D", max_amount: 400,
      listings: [{ indication: "Stage II or Stage III triple negative breast cancer", treatment_phase: null, level: "authority_required_streamlined", restriction_code: "x_R", conditions: [] }],
    }),
  ],
};

function renderAs(ui: React.ReactNode) {
  render(<ViewerProvider initialUser={userWith("clinician")}>{ui}</ViewerProvider>);
}

describe("PBS Drug Lookup", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pbs.fetchPbsSchedule.mockResolvedValue(STATUS);
    pbs.searchPbs.mockResolvedValue([
      { drug_name: "Pembrolizumab", brand_names: ["Keytruda"], item_code: "12120X", item_count: 14 },
    ]);
    pbs.fetchPbsDrug.mockResolvedValue(PEMBROLIZUMAB);
  });

  it("searches as you type and links each drug to its items", async () => {
    renderAs(<PbsPage />);
    fireEvent.change(await screen.findByLabelText("Drug, brand or active ingredient"), { target: { value: "pembro" } });
    await waitFor(() => expect(pbs.searchPbs).toHaveBeenLastCalledWith("pembro"));
    const row = (await screen.findByRole("link", { name: "Pembrolizumab" })).closest("li")!;
    expect(within(row).getByRole("link", { name: "Pembrolizumab" })).toHaveAttribute("href", "/pbs/12120X");
    expect(row).toHaveTextContent("Keytruda");
    expect(row).toHaveTextContent("14 PBS items");
  });

  it("says which schedule it shows", async () => {
    renderAs(<PbsPage />);
    expect(await screen.findByText(/As of 1 Sep 2026/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("warns when the data is the bundled sample", async () => {
    pbs.fetchPbsSchedule.mockResolvedValue({ ...STATUS, is_sample: true, current: { ...REFRESH, status: "partial", source: "sample" } });
    renderAs(<PbsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Sample data, not for clinical use");
  });

  it("warns when the last Refresh failed, and still shows the previous schedule", async () => {
    pbs.fetchPbsSchedule.mockResolvedValue({ ...STATUS, last_refresh: { ...REFRESH, status: "failed", refreshed_at: "2026-10-01T01:00:00Z" } });
    renderAs(<PbsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The last PBS Refresh failed");
    expect(screen.getByText(/As of 1 Sep 2026/)).toBeInTheDocument();
  });

  it("says when no schedule has been loaded", async () => {
    pbs.fetchPbsSchedule.mockResolvedValue({ ...STATUS, schedule_date: null, item_count: 0, current: null, last_refresh: null });
    renderAs(<PbsPage />);
    expect(await screen.findByText(/No PBS Schedule has been loaded yet/)).toBeInTheDocument();
  });

  it("shows a drug's items with their PBS Listing per indication, co-payments, quantities and conditions", async () => {
    renderAs(<PbsDrugPage params={{ itemCode: "12120X" }} />);
    expect(await screen.findByRole("heading", { name: "Pembrolizumab" })).toBeInTheDocument();
    expect(pbs.fetchPbsDrug).toHaveBeenCalledWith("12120X");
    const first = screen.getByRole("region", { name: "PBS item 12120X" });
    expect(within(first).getByText("12120X")).toHaveClass("font-mono");
    expect(first).toHaveTextContent("Efficient Funding of Chemotherapy (private hospital)");
    expect(first).toHaveTextContent("200 mg");
    expect(first).toHaveTextContent("7 repeats");
    expect(first).toHaveTextContent("$25.00 general");
    expect(first).toHaveTextContent("$7.70 concessional");
    const melanoma = within(first).getByText("Stage IIIB, Stage IIIC or Stage IIID malignant melanoma").closest("tr")!;
    expect(melanoma).toHaveTextContent("Initial treatment - 3 weekly treatment regimen");
    expect(within(melanoma).getByText("Authority Required")).toHaveClass("text-cau");
    expect(melanoma).toHaveTextContent("The treatment must be in addition to complete surgical resection; AND");

    const tnbc = within(screen.getByRole("region", { name: "PBS item 13739D" })).getByText("Stage II or Stage III triple negative breast cancer").closest("tr")!;
    expect(tnbc).toHaveTextContent("Authority Required (streamlined)");
    expect(await screen.findByText(/As of 1 Sep 2026/)).toBeInTheDocument();
    expect(screen.getByText(/Safety Net/)).toHaveTextContent("$1,748.20");
  });

  it("shows an Unrestricted item as listed for any indication", async () => {
    pbs.fetchPbsDrug.mockResolvedValue({
      drug_name: "Carboplatin", brand_names: ["Carboplatin Accord"], schedule_date: "2026-09-01",
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
