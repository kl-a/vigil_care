import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/clinical-data", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));
const clinical = vi.hoisted(() => ({ fetchConditions: vi.fn(), fetchEntryRights: vi.fn(), addCondition: vi.fn() }));
vi.mock("@/lib/clinical", async (importOriginal) => ({ ...(await importOriginal<object>()), ...clinical }));

import { Conditions } from "@/components/clinical/Conditions";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { stageLine, type CancerDiagnosisRow } from "@/modules/oncology/CancerDiagnoses";
import oncologyActive from "./contracts/oncology-active.json";
import { userWith } from "./fixtures";

const BREAST_TYPE = { key: "breast", display_name: "Breast cancer", mesh_term: "Breast Neoplasms", mesh_id: "D001943", staging_systems: ["TNM"] };
const diagnosis = (overrides: Partial<CancerDiagnosisRow>): CancerDiagnosisRow => ({
  id: "cd-1", condition_id: "c-1", name: "Breast cancer", cancer_type: BREAST_TYPE, histology: null, primary_site: null, laterality: "left",
  dx_date: "2024-03-01", stage_system: "TNM", stage: "IIA", disease_extent: "metastatic", disease_extent_as_of: "2026-09-01",
  cancer_status: "active", current_biomarkers: [], entered: null, ...overrides,
});

describe("Cancer Diagnosis", () => {
  it("reads Stage at diagnosis and Disease Extent now", () => {
    expect(stageLine(diagnosis({}))).toBe("Stage IIA (TNM) at diagnosis, 01/03/2024 · Metastatic as of 01/09/2026");
    expect(stageLine(diagnosis({ stage: null, disease_extent: "unknown", disease_extent_as_of: null }))).toBe("Stage not recorded · Unknown");
  });
});

describe("Add Condition with Oncology active", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clinical.fetchConditions.mockResolvedValue([
      { id: "c-1", name: "Breast cancer", status: "active", onset_date: null, notes: null, extended_by_module: "oncology", entered: null },
    ]);
    api.request.mockImplementation(async (path: string) => {
      if (path === "/modules/active") return oncologyActive;
      if (path === "/cancer-types") return [BREAST_TYPE];
      return diagnosis({});
    });
  });

  function renderConditions() {
    render(<ViewerProvider initialUser={userWith("clinician")}><Conditions patientId="pt-1" /></ViewerProvider>);
  }

  it("offers 'This is a primary cancer' to a clinician, opening the Cancer Diagnosis form", async () => {
    clinical.fetchEntryRights.mockResolvedValue({ condition: true, cancer_diagnosis: true });
    renderConditions();
    fireEvent.click(await screen.findByRole("button", { name: "Add Condition" }));
    fireEvent.click(await screen.findByLabelText("This is a primary cancer"));
    const form = await screen.findByRole("form", { name: "New Cancer Diagnosis" });
    await waitFor(() => expect(within(form).getByRole("option", { name: "Breast cancer" })).toBeInTheDocument());
    fireEvent.change(within(form).getByLabelText("Cancer Type"), { target: { value: "breast" } });
    expect(form).toHaveTextContent("MeSH: Breast Neoplasms");
    fireEvent.change(within(form).getByLabelText("Stage"), { target: { value: "IIA" } });
    fireEvent.click(within(form).getByRole("button", { name: "Record Cancer Diagnosis" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/cancer-diagnoses", expect.objectContaining({ method: "POST" })));
    const [, init] = api.request.mock.calls.find(([path]) => path === "/patients/pt-1/cancer-diagnoses")!;
    expect(JSON.parse(init.body)).toMatchObject({ cancer_type: "breast", stage: "IIA", disease_extent: "unknown", name: null });
  });

  it("doesn't offer it to a trial coordinator, who can't record one", async () => {
    clinical.fetchEntryRights.mockResolvedValue({ condition: true, cancer_diagnosis: false });
    renderConditions();
    fireEvent.click(await screen.findByRole("button", { name: "Add Condition" }));
    expect(screen.queryByLabelText("This is a primary cancer")).not.toBeInTheDocument();
    expect(screen.getByRole("form", { name: "New Condition" })).toBeInTheDocument();
  });

  it("sends a Condition a module extends to its own sub-tab for changes", async () => {
    clinical.fetchEntryRights.mockResolvedValue({ condition: true, cancer_diagnosis: true });
    renderConditions();
    const row = (await screen.findByText("Breast cancer")).closest("tr")!;
    expect(row).toHaveTextContent("Changed in its own sub-tab");
    expect(within(row).queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });
});
