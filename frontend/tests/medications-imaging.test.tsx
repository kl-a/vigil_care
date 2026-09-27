import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/medications", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));

import { Imaging } from "@/components/clinical/Imaging";
import { TreatmentCourses } from "@/components/clinical/TreatmentCourses";
import { MedicationManager, whatChanged } from "@/components/medications/MedicationManager";
import { PatientProvider } from "@/components/patients/PatientContext";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import type { ImagingStudyRow, TreatmentCourseRow } from "@/lib/clinical";
import { howTaken, type MedicationChangeRow, type MedicationRow } from "@/lib/medications";
import { isPartShipped } from "@/lib/stages";
import { ResponseAssessmentsTab, type ResponseAssessmentRow } from "@/modules/oncology/ResponseAssessments";
import oncologyActive from "./contracts/oncology-active.json";
import { userWith } from "./fixtures";

type Routes = Record<string, unknown>;

function respond(routes: Routes) {
  api.request.mockImplementation(async (path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET") return {};
    if (path === "/modules/active") return oncologyActive;
    if (path === "/patients/pt-1") return { id: "pt-1", display_name: "Jane Citizen", pseudonym: "P-1", identity: {}, history: [] };
    if (path in routes) return routes[path];
    return [];
  });
}

function renderIn(ui: React.ReactNode, jobTitle: "clinician" | "trial_coordinator" | "secretary" = "clinician") {
  render(<ViewerProvider initialUser={userWith(jobTitle)}><PatientProvider patientId="pt-1">{ui}</PatientProvider></ViewerProvider>);
}

const MED = (overrides: Partial<MedicationRow>): MedicationRow => ({
  id: "m-1", drug_reference_id: "d-1", drug_name: "Dexamfetamine", generic_name: "Dexamfetamine", in_drug_reference: true, is_cancer_drug: false,
  pbs_item_codes: ["1165H"], brand_name: null, dose_amount: "5", dose_unit: "mg", dose_display: "5 mg", frequency: "twice_daily", frequency_detail: null,
  route: "oral", indication: "Fatigue", category: "supportive_care", start_date: "2026-06-01", end_date: null, status: "active", reason_discontinued: null,
  prescribed_by_provider_id: null, prescriber_name: "Dr Alex Rivera", treatment_course_id: null, treatment_course_name: null, notes: null,
  source: "doctor_entered", entered: null, ...overrides,
});
const MEDS = [
  MED({}),
  MED({ id: "m-2", drug_reference_id: null, drug_name: "Turmeric capsules", in_drug_reference: false, pbs_item_codes: [], dose_display: null, dose_amount: null, frequency: null, route: null }),
  MED({ id: "m-3", drug_name: "Dexamethasone", pbs_item_codes: ["2507Y"], status: "discontinued", end_date: "2026-07-01", reason_discontinued: "Course of steroids finished" }),
];
const LOG: MedicationChangeRow[] = [
  { id: "l-2", medication_id: "m-1", drug_name: "Dexamfetamine", change_type: "dose_changed", previous_value: { dose_amount: "10" }, new_value: { dose_amount: "5" },
    by: "Dr Alex Rivera", at: "2026-09-01T01:00:00Z", reason: "Insomnia" },
  { id: "l-1", medication_id: "m-1", drug_name: "Dexamfetamine", change_type: "added", previous_value: null, new_value: { dose_amount: "10" },
    by: "Sam Lee", at: "2026-06-01T01:00:00Z", reason: null },
];
const MEDICATION_ROUTES: Routes = {
  "/clinical/entry-rights": { medication: true }, "/patients/pt-1/medications": MEDS, "/patients/pt-1/medication-changes": LOG,
};

describe("Medication Manager", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists active Medications, linking drug-reference ones to the PBS Drug Lookup", async () => {
    respond(MEDICATION_ROUTES);
    renderIn(<MedicationManager />);
    const table = await screen.findByRole("table", { name: "Active medications" });
    const dex = within(table).getByText("Dexamfetamine").closest("tr")!;
    expect(dex).toHaveTextContent("5 mg · Oral · Twice daily");
    expect(within(dex).getByRole("link", { name: "PBS Drug Lookup" })).toHaveAttribute("href", "/pbs/1165H");
    const turmeric = within(table).getByText("Turmeric capsules").closest("tr")!;
    expect(turmeric).toHaveTextContent("Not in the drug reference");
    expect(within(table).queryByText("Dexamethasone")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Discontinued (1)" })).toBeInTheDocument();
  });

  it("shows discontinued Medications with why, and the change log with who and why", async () => {
    respond(MEDICATION_ROUTES);
    renderIn(<MedicationManager />);
    fireEvent.click(await screen.findByRole("button", { name: "Discontinued (1)" }));
    expect(screen.getByRole("table", { name: "Discontinued medications" })).toHaveTextContent("Course of steroids finished");
    fireEvent.click(screen.getByRole("button", { name: "Change log" }));
    const change = within(screen.getByRole("table", { name: "Change log" })).getByText("Dose changed").closest("tr")!;
    expect(change).toHaveTextContent("Dose: 10 → 5");
    expect(change).toHaveTextContent("Dr Alex Rivera");
    expect(change).toHaveTextContent("Insomnia");
  });

  it("stops a Medication with the date and why", async () => {
    respond(MEDICATION_ROUTES);
    renderIn(<MedicationManager />);
    const table = await screen.findByRole("table", { name: "Active medications" });
    fireEvent.click(within(within(table).getByText("Dexamfetamine").closest("tr")!).getByRole("button", { name: "Stop" }));
    const dialog = await screen.findByRole("dialog", { name: "Stop Dexamfetamine" });
    fireEvent.change(within(dialog).getByLabelText("Stopped on"), { target: { value: "2026-09-20" } });
    fireEvent.change(within(dialog).getByLabelText("Reason (required)"), { target: { value: "Fatigue resolved" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Stop" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/medications/m-1/stop", {
      method: "POST", body: JSON.stringify({ end_date: "2026-09-20", reason: "Fatigue resolved" }),
    }));
  });

  it("lets a secretary read but not add or change", async () => {
    respond({ ...MEDICATION_ROUTES, "/clinical/entry-rights": { medication: false } });
    renderIn(<MedicationManager />, "secretary");
    const table = await screen.findByRole("table", { name: "Active medications" });
    expect(within(table).queryByRole("button", { name: "Stop" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add medication" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument();
  });

  it("describes how a Medication is taken and what a change changed", () => {
    expect(howTaken({ dose_display: null, route: null, frequency: null, frequency_detail: null })).toBe("Dose not recorded");
    expect(howTaken({ dose_display: "1 g", route: "iv", frequency: "other", frequency_detail: "Day 1 and 8" })).toBe("1 g · IV · Day 1 and 8");
    expect(whatChanged({ change_type: "corrected", previous_value: { indication: null }, new_value: { indication: "Nausea" } })).toBe("For: none → Nausea");
    expect(whatChanged({ change_type: "corrected", previous_value: {}, new_value: null })).toBe("Removed (entered by mistake)");
  });
});

const CT: ImagingStudyRow = {
  id: "s-1", modality: "CT", body_region: "Chest, abdomen and pelvis", study_date: "2026-08-14", comparison_date: "2026-05-10",
  impression: "Interval decrease in hepatic metastases.\n  No new lesions.", entered: null,
  findings: [{ id: "f-1", site: "Liver segment VII", laterality: null, description: "Metastasis", size_mm: "18", suv_max: null, is_new: false, is_measurable: true, condition_id: null, condition_name: null, entered: null }],
};
const RESPONDING: ResponseAssessmentRow = {
  id: "ra-1", cancer_diagnosis_id: "cd-1", cancer_diagnosis_name: "Breast cancer", assessed_on: "2026-08-14", direction: "responding",
  source: "radiology_report", imaging_study_id: "s-1", overrides_id: null, overridden_by_id: null, override_reason: null, entered: null,
};

describe("Imaging & Findings", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a scan's impression verbatim, its Findings, and Oncology's Response Assessment badge", async () => {
    respond({ "/clinical/entry-rights": { imaging_study: true, finding: true }, "/patients/pt-1/imaging-studies": [CT], "/patients/pt-1/response-assessments": [RESPONDING] });
    renderIn(<Imaging patientId="pt-1" />);
    const scan = await screen.findByRole("article", { name: "CT chest, abdomen and pelvis, 14/08/2026" });
    expect(within(scan).getByText(/Interval decrease/).textContent).toBe("Interval decrease in hepatic metastases.\n  No new lesions.");
    expect(within(scan).getByRole("table", { name: "Findings" })).toHaveTextContent("Liver segment VII");
    expect(await within(scan).findByText("Responding")).toBeInTheDocument();
    expect(within(scan).getByText("(latest)")).toBeInTheDocument();
  });

  it("corrects a scan with one reason per save, and asks for none when nothing changed", async () => {
    respond({ "/clinical/entry-rights": { imaging_study: true, finding: true }, "/patients/pt-1/imaging-studies": [CT] });
    renderIn(<Imaging patientId="pt-1" />);
    const scan = await screen.findByRole("article", { name: "CT chest, abdomen and pelvis, 14/08/2026" });
    fireEvent.click(within(scan).getByRole("button", { name: "Correct" }));
    fireEvent.click(within(await screen.findByRole("form", { name: "Correct CT chest, abdomen and pelvis" })).getByRole("button", { name: "Save" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(within(scan).getByRole("button", { name: "Correct" }));
    const form = await screen.findByRole("form", { name: "Correct CT chest, abdomen and pelvis" });
    fireEvent.change(within(form).getByLabelText("Body region"), { target: { value: "Chest" } });
    fireEvent.click(within(form).getByRole("button", { name: "Save" }));
    const dialog = await screen.findByRole("dialog", { name: "Save changes to CT chest, abdomen and pelvis" });
    fireEvent.change(within(dialog).getByLabelText("Reason (required)"), { target: { value: "Typo" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/imaging-studies/s-1", {
      method: "PATCH", body: JSON.stringify({ body_region: "Chest", reason: "Typo" }),
    }));
  });

  it("adds a Finding to a scan already recorded", async () => {
    respond({ "/clinical/entry-rights": { imaging_study: true, finding: true }, "/patients/pt-1/imaging-studies": [CT] });
    renderIn(<Imaging patientId="pt-1" />);
    const scan = await screen.findByRole("article", { name: "CT chest, abdomen and pelvis, 14/08/2026" });
    fireEvent.click(within(scan).getByRole("button", { name: "Add finding" }));
    const form = within(scan).getByRole("form", { name: "New Finding" });
    fireEvent.change(within(form).getByLabelText("Finding 1"), { target: { value: "Sclerotic lesion" } });
    fireEvent.change(within(form).getByLabelText("Site 1"), { target: { value: "T10" } });
    fireEvent.click(within(form).getByRole("button", { name: "Add finding" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/imaging-studies/s-1/findings", expect.objectContaining({ method: "POST" })));
  });
});

describe("Response Assessments", () => {
  beforeEach(() => vi.clearAllMocks());
  const UNSURE: ResponseAssessmentRow = { ...RESPONDING, id: "ra-2", cancer_diagnosis_id: null, cancer_diagnosis_name: null, direction: "progressing", imaging_study_id: null };

  function routes(clinician: boolean): Routes {
    return {
      "/clinical/entry-rights": { response_assessment: true, response_assessment_override: clinician },
      "/patients/pt-1/response-assessments": [UNSURE, RESPONDING], "/patients/pt-1/cancer-diagnoses": [{ id: "cd-1", name: "Breast cancer" }],
      "/patients/pt-1/imaging-studies": [CT],
    };
  }

  it("lets a clinician attribute one recorded as 'not sure which Cancer Diagnosis', or override one", async () => {
    respond(routes(true));
    renderIn(<ResponseAssessmentsTab />);
    const unsure = (await screen.findByText("Not sure which Cancer Diagnosis")).closest("li")!;
    fireEvent.change(within(unsure).getByLabelText("Attribute to"), { target: { value: "cd-1" } });
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/response-assessments/ra-2/attribute", {
      method: "POST", body: JSON.stringify({ cancer_diagnosis_id: "cd-1" }),
    }));
    const reported = within(screen.getByRole("list", { name: "Response Assessments" })).getAllByRole("listitem")[1]!;
    expect(reported).toHaveTextContent("Radiology report · CT chest, abdomen and pelvis, 14/08/2026");
    fireEvent.click(within(reported).getByRole("button", { name: "Override" }));
    expect(await screen.findByRole("dialog", { name: "Override this Response Assessment" })).toBeInTheDocument();
  });

  it("shows a trial coordinator the assessments but not a clinician's decisions", async () => {
    respond(routes(false));
    renderIn(<ResponseAssessmentsTab />, "trial_coordinator");
    const unsure = (await screen.findByText("Not sure which Cancer Diagnosis")).closest("li")!;
    expect(within(unsure).queryByLabelText("Attribute to")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Override" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record assessment" })).toBeInTheDocument();
  });

  it("gives a course its derived best response, as a status with an icon", async () => {
    const course = { id: "tc-1", condition_id: "c-1", condition_name: "Breast cancer", modality: "systemic", intent: "palliative", regimen_name: "Paclitaxel",
      regimen_drugs: [], start_date: "2026-05-12", end_date: null, ongoing: true, reason_stopped: null, details: null, entered: null } as TreatmentCourseRow;
    respond({
      "/clinical/entry-rights": {}, "/patients/pt-1/treatment-courses": [course],
      "/patients/pt-1/best-responses": [{ treatment_course_id: "tc-1", direction: "responding", response_assessment_id: "ra-1", imaging_study_id: "s-1",
        explanation: "Responding: best response during Paclitaxel, on CT of 14 Aug 2026" }],
    });
    renderIn(<TreatmentCourses patientId="pt-1" />);
    const badge = await screen.findByText("Best Response: Responding");
    expect(badge.closest("span.rounded-full")!.querySelector("svg")).not.toBeNull();
    expect(screen.getByText("Responding: best response during Paclitaxel, on CT of 14 Aug 2026")).toBeInTheDocument();
  });
});

describe("Stage 4 ships 4b and 4c", () => {
  it("shows every part of Stage 4", () => {
    expect(["4a", "4b", "4c"].every((part) => isPartShipped(part))).toBe(true);
  });
});
