import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/clinical-data", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const clinical = vi.hoisted(() => ({
  fetchEntryRights: vi.fn(), fetchLabResults: vi.fn(), addLabPanel: vi.fn(), removeLabResult: vi.fn(),
  fetchManagementPlans: vi.fn(), addManagementPlan: vi.fn(), fetchClinicalNotes: vi.fn(), addClinicalNote: vi.fn(),
  removeClinicalNote: vi.fn(), fetchNextSteps: vi.fn(), addNextStep: vi.fn(), markNextStepDone: vi.fn(), removeNextStep: vi.fn(),
}));
vi.mock("@/lib/clinical", async (importOriginal) => ({ ...(await importOriginal<object>()), ...clinical }));
const providers = vi.hoisted(() => ({ listProviders: vi.fn() }));
vi.mock("@/lib/providers", async (importOriginal) => ({ ...(await importOriginal<object>()), ...providers }));

import { Labs, TrendChart } from "@/components/clinical/Labs";
import { PlanAndNotes } from "@/components/clinical/PlanAndNotes";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { trendsOf, type LabResultRow } from "@/lib/clinical";
import { userWith } from "./fixtures";

const ENTERED = { by: "Sam Lee (synthetic)", job_title: "trial_coordinator" as const, at: "2026-09-20T01:00:00Z" };
const lab = (overrides: Partial<LabResultRow>): LabResultRow => ({
  id: "l-1", panel_id: "p-1", panel: "FBC", analyte: "Haemoglobin", value: "98", value_text: null, unit: "g/L",
  ref_low: "115", ref_high: "165", flag: "low", collected_at: "2026-09-20T08:30:00+10:00", entered: ENTERED, ...overrides,
});

function renderAs(ui: React.ReactNode, jobTitle: "clinician" | "secretary" = "clinician") {
  render(<ViewerProvider initialUser={userWith(jobTitle)}>{ui}</ViewerProvider>);
}

describe("Labs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clinical.fetchEntryRights.mockResolvedValue({ lab_result: true });
    clinical.fetchLabResults.mockResolvedValue([
      lab({ id: "l-2", value: "105", collected_at: "2026-09-27T09:00:00+10:00" }),
      lab({}),
      lab({ id: "l-3", analyte: "Blood film", value: null, value_text: "Normochromic", unit: null, ref_low: null, ref_high: null, flag: null }),
    ]);
    clinical.addLabPanel.mockResolvedValue({});
  });

  it("lists results with their flags from the report's range", async () => {
    renderAs(<Labs patientId="pt-1" />);
    const table = await screen.findByRole("table", { name: "Lab results" });
    const row = within(table).getAllByText("Haemoglobin").map((cell) => cell.closest("tr")!).find((tr) => tr.textContent?.includes("98 g/L"))!;
    expect(row).toHaveTextContent("98 g/L");
    expect(within(row).getByLabelText("low")).toHaveTextContent("L");
    expect(row).toHaveTextContent("115–165");
    expect(screen.getByText("Normochromic").closest("tr")).toHaveTextContent("—");
  });

  it("enters a panel in one save, prefilled with its common analytes, skipping empty ones", async () => {
    renderAs(<Labs patientId="pt-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Enter results" }));
    const form = screen.getByRole("form", { name: "Enter results" });
    fireEvent.change(within(form).getByLabelText("Collected on"), { target: { value: "2026-09-27" } });
    fireEvent.change(within(form).getByLabelText("Panel"), { target: { value: "FBC" } });
    fireEvent.change(within(form).getByLabelText("Haemoglobin value"), { target: { value: "105" } });
    fireEvent.change(within(form).getByLabelText("Haemoglobin ref low"), { target: { value: "115" } });
    fireEvent.change(within(form).getByLabelText("Haemoglobin ref high"), { target: { value: "165" } });
    fireEvent.change(within(form).getByLabelText("Platelets value"), { target: { value: "<20" } });
    fireEvent.click(within(form).getByRole("button", { name: "Save panel" }));
    await waitFor(() => expect(clinical.addLabPanel).toHaveBeenCalledWith("pt-1", {
      collected_on: "2026-09-27", collected_time: null, panel: "FBC", results: [
        { analyte: "Haemoglobin", unit: "g/L", ref_low: "115", ref_high: "165", value: "105" },
        { analyte: "Platelets", unit: "x10^9/L", ref_low: null, ref_high: null, value_text: "<20" },
      ],
    }));
  });

  it("charts a trend with the reference range shaded", async () => {
    renderAs(<Labs patientId="pt-1" />);
    // The first analyte recorded is charted first.
    expect(await screen.findByRole("img", { name: "Haemoglobin trend" })).toBeInTheDocument();
    expect(screen.getByTestId("reference-band")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Trend"), { target: { value: "Blood film" } });
    expect(screen.getByText("No numeric results to chart for Blood film.")).toBeInTheDocument();
  });

  it("is read-only for a secretary", async () => {
    clinical.fetchEntryRights.mockResolvedValue({ lab_result: false });
    renderAs(<Labs patientId="pt-1" />, "secretary");
    expect(await screen.findByText("Needs clinician/coordinator")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enter results" })).not.toBeInTheDocument();
  });

  it("builds trends oldest first per analyte", () => {
    const trends = trendsOf([lab({ id: "b", collected_at: "2026-09-27T00:00:00Z" }), lab({ id: "a" })]);
    expect(trends.get("Haemoglobin")!.map((r) => r.id)).toEqual(["a", "b"]);
  });
});

describe("TrendChart", () => {
  it("says so when there is nothing numeric", () => {
    render(<TrendChart analyte="Film" results={[lab({ value: null, value_text: "Normal" })]} />);
    expect(screen.getByText("No numeric results to chart for Film.")).toBeInTheDocument();
  });
});

describe("Plan and notes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    providers.listProviders.mockResolvedValue([{ id: "pr-1", display_name: "Dr Alex Rivera" }]);
    clinical.fetchEntryRights.mockResolvedValue({ management_plan: true, clinical_note: true });
    clinical.fetchManagementPlans.mockResolvedValue([
      { id: "mp-2", plan_text: "Start palliative chemotherapy.\n  Review in 3 weeks.", plan_date: "2026-09-20", authored_by_provider_id: "pr-1", author_name: "Dr Alex Rivera", entered: ENTERED },
      { id: "mp-1", plan_text: "Continue letrozole.", plan_date: "2026-06-01", authored_by_provider_id: null, author_name: null, entered: ENTERED },
    ]);
    clinical.fetchClinicalNotes.mockResolvedValue([]);
    clinical.fetchNextSteps.mockResolvedValue([
      { id: "ns-1", kind: "mdt", description: "Discuss at breast MDT", due_date: "2026-10-02", entered: ENTERED, done: null },
      { id: "ns-2", kind: "review", description: "Clinic review", due_date: "2026-09-01", entered: ENTERED, done: { by: "Jordan Park (synthetic)", at: "2026-09-01T02:00:00Z" } },
    ]);
    clinical.markNextStepDone.mockResolvedValue({});
    clinical.addManagementPlan.mockResolvedValue({});
  });

  it("quotes the current plan verbatim with its author, keeping earlier plans", async () => {
    renderAs(<PlanAndNotes patientId="pt-1" />);
    const quote = await screen.findByText((_, el) => el?.tagName === "BLOCKQUOTE" && el.textContent === "Start palliative chemotherapy.\n  Review in 3 weeks.");
    expect(quote.closest("figure")).toHaveTextContent("Dr Alex Rivera");
    expect(screen.getByText("Earlier plans (1)")).toBeInTheDocument();
  });

  it("records a new plan exactly as typed", async () => {
    renderAs(<PlanAndNotes patientId="pt-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Record new plan" }));
    const form = screen.getByRole("form", { name: "New Management Plan" });
    fireEvent.change(within(form).getByLabelText("Plan, exactly as written in the letter"), { target: { value: "  Re-stage CT.  " } });
    fireEvent.change(within(form).getByLabelText("Written by"), { target: { value: "pr-1" } });
    fireEvent.click(within(form).getByRole("button", { name: "Save plan" }));
    await waitFor(() => expect(clinical.addManagementPlan).toHaveBeenCalledWith("pt-1", expect.objectContaining({ plan_text: "  Re-stage CT.  ", authored_by_provider_id: "pr-1" })));
  });

  it("lists Next Steps and marks one done; a secretary can too", async () => {
    clinical.fetchEntryRights.mockResolvedValue({ management_plan: false, clinical_note: false });
    renderAs(<PlanAndNotes patientId="pt-1" />, "secretary");
    const open = (await screen.findByText("Discuss at breast MDT")).closest("li")!;
    expect(open).toHaveTextContent("MDT · due 02/10/2026");
    expect(screen.getByText("Clinic review").closest("li")).toHaveTextContent("done by Jordan Park (synthetic)");
    fireEvent.click(within(open).getByRole("button", { name: "Mark done" }));
    await waitFor(() => expect(clinical.markNextStepDone).toHaveBeenCalledWith("pt-1", "ns-1"));
    expect(screen.getAllByText("Needs clinician/coordinator")).toHaveLength(2);  // plan and notes, not Next Steps
  });
});
