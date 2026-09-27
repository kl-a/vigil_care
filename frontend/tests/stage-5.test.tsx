import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));

import { Dashboard } from "@/components/dashboard/Dashboard";
import { OpenItemCards, OpenItemList, OpenItemTable } from "@/components/openItems/OpenItemList";
import { PatientProvider } from "@/components/patients/PatientContext";
import { Sidebar } from "@/components/shell/Sidebar";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { PatientSummary } from "@/components/summary/PatientSummary";
import { ageOf, type OpenItem, type PatientSummary as Summary } from "@/lib/summary";
import { SHIPPED_STAGE } from "@/lib/stages";
import { NO_MODULES } from "@/lib/modules/types";
import { ONCOLOGY_ON, userWith } from "./fixtures";

const NEXT_STEP: OpenItem = {
  type: "next_step", type_label: "Next Step", patient_id: "pt-1", patient_name: "Robin Sample", title: "Discuss lung nodule at MDT",
  detail: "Due 30 Sep 2026", dated: "2026-09-30", who: "staff", icon: "calendar", subject_table: "next_step", subject_id: "ns-1", open_tab: "clinical-data",
  actions: [{ label: "Mark done", path: "/patients/pt-1/next-steps/ns-1/done", input: "none", field: null, choices: [] }],
};
const DIFFERING: OpenItem = {
  type: "differing_biomarker_results", type_label: "Differing Biomarker Results", patient_id: "pt-1", patient_name: "Robin Sample",
  title: "BRAF V600E results differ", detail: "Colorectal cancer: negative (14 May 2024); positive (20 Feb 2026)", dated: "2026-02-20",
  who: "clinician", icon: "compare", subject_table: "biomarker", subject_id: "b-2", open_tab: "clinical-data",
  actions: [{ label: "Seen", path: "/patients/pt-1/cancer-diagnoses/cd-1/biomarkers/b-2/seen", input: "note", field: null, choices: [] }],
};
const UNATTRIBUTED: OpenItem = {
  ...DIFFERING, type: "unattributed_response_assessment", type_label: "Unattributed Response Assessment", title: "Response Assessment not attributed: stable",
  subject_id: "ra-1", subject_table: "response_assessment", icon: "help",
  actions: [{ label: "Attribute", path: "/patients/pt-1/response-assessments/ra-1/attribute", input: "choose", field: "cancer_diagnosis_id",
    choices: [{ id: "cd-1", name: "Colorectal cancer" }, { id: "cd-2", name: "Melanoma, left forearm" }] }],
};

function renderAs(jobTitle: "clinician" | "secretary", ui: React.ReactNode) {
  render(<ViewerProvider initialUser={userWith(jobTitle)} loadModules={async () => NO_MODULES}>{ui}</ViewerProvider>);
}

describe("Open Items", () => {
  beforeEach(() => { vi.clearAllMocks(); api.request.mockResolvedValue(undefined); });

  it("act in one click, or through a small popover when they need a note or a choice", async () => {
    const onActed = vi.fn();
    renderAs("clinician", <OpenItemTable items={[NEXT_STEP, DIFFERING, UNATTRIBUTED]} onActed={onActed} />);
    fireEvent.click(within(screen.getByText("Discuss lung nodule at MDT").closest("tr")!).getByRole("button", { name: "Mark done" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith(NEXT_STEP.actions[0]!.path, { method: "POST", body: "{}" }));
    fireEvent.click(within(screen.getByText("BRAF V600E results differ").closest("tr")!).getByRole("button", { name: "Seen" }));
    const seen = await screen.findByRole("dialog", { name: "Seen" });
    fireEvent.change(within(seen).getByLabelText("Note (optional)"), { target: { value: "Discussed at MDT" } });
    fireEvent.click(within(seen).getByRole("button", { name: "Seen" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith(DIFFERING.actions[0]!.path, { method: "POST", body: JSON.stringify({ note: "Discussed at MDT" }) }));
    fireEvent.click(within(screen.getByText(/not attributed/).closest("tr")!).getByRole("button", { name: "Attribute" }));
    const attribute = await screen.findByRole("dialog", { name: "Attribute" });
    expect(within(attribute).getByRole("button", { name: "Attribute" })).toBeDisabled();
    fireEvent.change(within(attribute).getByLabelText("Attribute to"), { target: { value: "cd-2" } });
    fireEvent.click(within(attribute).getByRole("button", { name: "Attribute" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith(UNATTRIBUTED.actions[0]!.path, { method: "POST", body: JSON.stringify({ cancer_diagnosis_id: "cd-2" }) }));
    expect(onActed).toHaveBeenCalledTimes(3);
  });

  it("put a second action behind ⋯, and ask why before ruling out", async () => {
    const recurrence: OpenItem = { ...DIFFERING, type: "suspected_recurrence", type_label: "Suspected Recurrence", icon: "alert", title: "Suspected Recurrence of Melanoma",
      actions: [{ label: "Confirm", path: "/patients/pt-1/recurrences/r-1/confirm", input: "none", field: null, choices: [] },
        { label: "Rule out", path: "/patients/pt-1/recurrences/r-1/rule-out", input: "reason", field: null, choices: [] }] };
    renderAs("clinician", <OpenItemCards items={[recurrence]} onActed={vi.fn()} />);
    const card = screen.getByText("Suspected Recurrence of Melanoma").closest("li")!;
    expect(within(card).getByText("Suspected Recurrence").querySelector("svg")).not.toBeNull();
    fireEvent.click(within(card).getByRole("button", { name: "More actions: Suspected Recurrence of Melanoma" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Rule out" }));
    const dialog = await screen.findByRole("dialog", { name: "Rule out" });
    expect(within(dialog).getByRole("button", { name: "Rule out" })).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText("Why (required)"), { target: { value: "Benign on biopsy" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Rule out" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/recurrences/r-1/rule-out", { method: "POST", body: JSON.stringify({ reason: "Benign on biopsy" }) }));
  });

  it("show a secretary clinician-only items as 'Needs clinician', and let them mark a Next Step done", () => {
    renderAs("secretary", <OpenItemList items={[NEXT_STEP, DIFFERING]} onActed={vi.fn()} />);
    const differing = screen.getByText("BRAF V600E results differ").closest("li")!;
    expect(within(differing).queryByRole("button", { name: "Seen" })).not.toBeInTheDocument();
    expect(differing).toHaveTextContent(/Needs clinician/);
    expect(within(screen.getByText("Discuss lung nodule at MDT").closest("li")!).getByRole("button", { name: "Mark done" })).toBeInTheDocument();
  });

  it("never offer a dismiss or snooze", () => {
    renderAs("clinician", <OpenItemTable items={[NEXT_STEP, DIFFERING, UNATTRIBUTED]} onActed={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /dismiss|snooze|hide/i })).not.toBeInTheDocument();
  });

  it("say how long each has waited, or when a Next Step is due", () => {
    const today = new Date(2026, 8, 27);
    expect(ageOf({ type: "next_step", dated: "2026-09-30" }, today)).toBe("due 3 d");
    expect(ageOf({ type: "next_step", dated: "2026-09-25" }, today)).toBe("2 d overdue");
    expect(ageOf({ type: "differing_biomarker_results", dated: "2026-09-20" }, today)).toBe("7 d");
    expect(ageOf({ type: "differing_biomarker_results", dated: "2026-02-20" }, today)).toBe("7 mo");
  });
});

describe("Dashboard", () => {
  beforeEach(() => { vi.clearAllMocks(); api.request.mockImplementation(async (path: string) => (path === "/open-items" ? [NEXT_STEP, DIFFERING, UNATTRIBUTED] : path === "/refreshes" ? [] : null)); });

  it("lists the Practice's Open Items as a table with their Patients, filtered by type and by who can act", async () => {
    renderAs("secretary", <Dashboard />);
    const table = await screen.findByRole("table", { name: "Open Items" });
    expect(screen.getByText("3 across the practice")).toBeInTheDocument();
    expect(within(table).getAllByRole("link", { name: "Robin Sample" })[0]).toHaveAttribute("href", "/patients/pt-1/summary");
    const rows = () => within(screen.getByRole("table", { name: "Open Items" })).getAllByRole("row").slice(1);
    expect(rows()).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: "Differing Biomarker Results (1)" }));
    expect(rows()).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "All (3)" }));
    fireEvent.click(screen.getByRole("button", { name: "I can act" }));
    expect(rows().map((row) => row.textContent)).toEqual([expect.stringContaining("Discuss lung nodule at MDT")]);
    fireEvent.click(screen.getByRole("button", { name: "Clinician only" }));
    expect(rows()).toHaveLength(2);
    expect(screen.getByRole("region", { name: "Reference data" })).toHaveTextContent("PBS Schedule");
  });
});

const EMPTY_SUMMARY: Summary = {
  results: { latest_labs: [], lab_trends: {}, scans: [], updated: null },
  treatment: { courses: [], updated: null },
  notes: { latest_note: null, latest_letter: null, updated: null },
  management: { plan: null, next_steps: [], updated: null },
  history: { comorbidities: [], medications: [], updated: null },
  open_items: [],
};
const PATIENT = {
  id: "pt-1", display_name: "Robin Sample", pseudonym: "VG-0044", identity: { given_name: "Robin", family_name: "Sample", dob: "1958-01-29", medicare_number: "0000 00044 1" },
  history: [{ action: "edit", at: "2026-09-01T01:00:00Z", by_display_name: "Jordan Park", by_job_title: "secretary", before: null, after: null, reason: null }],
};

describe("Patient Summary", () => {
  function respond(summary: Summary) {
    api.request.mockImplementation(async (path: string) => {
      if (path === "/patients/pt-1") return PATIENT;
      if (path === "/patients/pt-1/summary") return summary;
      return [];
    });
  }
  beforeEach(() => vi.clearAllMocks());

  it("shows every section, saying 'None recorded' when empty, never hiding it", async () => {
    respond(EMPTY_SUMMARY);
    renderAs("clinician", <PatientProvider patientId="pt-1"><PatientSummary /></PatientProvider>);
    for (const title of ["Registration", "Most Recent Results", "Recent Treatment", "Clinical Notes", "Management", "Medical History", "Open Items"]) {
      expect(await screen.findByRole("heading", { name: new RegExp(`^${title}`) })).toBeInTheDocument();
    }
    const history = screen.getByRole("region", { name: "Medical History" });
    expect(within(history).getAllByText("None recorded")).toHaveLength(2);
    expect(screen.getByRole("region", { name: "Registration" })).toHaveTextContent("0000 00044 1");
    expect(screen.getByRole("button", { name: "Print summary" })).toBeInTheDocument();
    // The glance strip keeps its tiles, saying what isn't recorded.
    const glance = screen.getByRole("region", { name: "At a glance" });
    expect(glance).toHaveTextContent("TreatmentNot recorded");
    expect(glance).toHaveTextContent("Next stepNot recorded");
    // No module draws a Diagnosis: the section still shows, saying so.
    expect(within(await screen.findByRole("region", { name: "Diagnosis" })).getByText("None recorded")).toBeInTheDocument();
  });

  it("says who last updated a section, with their Job Title, and links to it in the record", async () => {
    respond({
      ...EMPTY_SUMMARY,
      history: {
        comorbidities: [{ id: "c-1", name: "Type 2 diabetes", status: "active", onset_date: null, notes: null, extended_by_module: null, entered: null }],
        medications: [],
        updated: { by: "Sam Lee", job_title: "trial_coordinator", at: "2026-09-14T01:00:00Z", action: "edit", subject_table: "condition", subject_id: "c-1" },
      },
    });
    renderAs("clinician", <PatientProvider patientId="pt-1"><PatientSummary /></PatientProvider>);
    const history = await screen.findByRole("region", { name: "Medical History" });
    expect(within(history).getByText("Type 2 diabetes")).toBeInTheDocument();
    expect(within(history).getByRole("button", { name: /^Verified by Sam Lee \(Trial coordinator\)/ })).toBeInTheDocument();
    expect(within(history).getByRole("link", { name: "See it in the record" })).toHaveAttribute("href", "/patients/pt-1/clinical-data?tab=conditions");
  });
});

describe("The Summary's hierarchy (#53)", () => {
  beforeEach(() => vi.clearAllMocks());
  const lab = (analyte: string, value: string, flag: string, low: string | null, high: string | null) => ({
    id: analyte, panel_id: "p", panel: "FBC", analyte, value, value_text: null, unit: "g/L", ref_low: low, ref_high: high, flag,
    collected_at: "2026-09-14T00:00:00Z", entered: null,
  });

  it("puts Oncology's tiles among the Core's, and flagged results first with the rest collapsed", async () => {
    api.request.mockImplementation(async (path: string) => {
      if (path === "/modules/active") return ONCOLOGY_ON;
      if (path === "/patients/pt-1") return PATIENT;
      if (path === "/patients/pt-1/summary") return {
        ...EMPTY_SUMMARY,
        results: { ...EMPTY_SUMMARY.results, latest_labs: [lab("Platelets", "160", "normal", "150", "400"), lab("Haemoglobin", "104", "low", "115", "165")],
          lab_trends: { Haemoglobin: [{ collected_at: "2026-06-08T00:00:00Z", value: "112" }, { collected_at: "2026-09-14T00:00:00Z", value: "104" }] } },
        treatment: { courses: [{ id: "tc-1", condition_id: "c-1", condition_name: "Colorectal cancer", modality: "systemic", intent: "palliative",
          regimen_name: "FOLFOX + bevacizumab", regimen_drugs: [], start_date: "2026-03-02", end_date: null, ongoing: true, reason_stopped: null, details: null, entered: null }], updated: null },
      };
      if (path === "/patients/pt-1/cancer-diagnoses") return [{ id: "cd-1", name: "Colorectal cancer", stage: "IIIB", disease_extent: "metastatic", cancer_status: "active", current_biomarkers: [], cancer_type: { display_name: "Colorectal cancer" } }];
      if (path === "/patients/pt-1/performance-status") return [{ id: "e-1", scale: "ECOG", value: 1, assessed_on: "2026-09-14", entered: null }];
      if (path === "/patients/pt-1/diagnosis-updated") return null;
      return [];
    });
    render(<ViewerProvider initialUser={userWith("clinician")} loadModules={async () => ONCOLOGY_ON}><PatientProvider patientId="pt-1"><PatientSummary /></PatientProvider></ViewerProvider>);
    const glance = await screen.findByRole("region", { name: "At a glance" });
    await vi.waitFor(() => expect(within(glance).getAllByText(/^(Diagnosis|Treatment|Latest response|ECOG|Next step)$/).map((t) => t.textContent))
      .toEqual(["Diagnosis", "Treatment", "Latest response", "ECOG", "Next step"]));
    expect(glance).toHaveTextContent("Colorectal cancerStage IIIB at dx · now metastatic");
    expect(glance).toHaveTextContent("FOLFOX + bevacizumabsince 2 Mar 2026 · ongoing");
    const bloods = screen.getByRole("list", { name: "Latest bloods" });
    expect(within(bloods).getAllByRole("listitem").map((li) => li.textContent?.split("g/L")[0])).toEqual(["Haemoglobin"]);
    expect(bloods).toHaveTextContent("Low");
    fireEvent.click(screen.getByRole("button", { name: "Show" }));
    expect(within(bloods).getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("Stage 5", () => {
  it("has shipped", () => expect(SHIPPED_STAGE).toBe(5));
});

describe("The Dashboard's count in the sidebar", () => {
  it("counts only the Open Items this User can act on, and none for the developer admin", async () => {
    api.request.mockImplementation(async (path: string) => (path === "/open-items" ? [NEXT_STEP, DIFFERING, UNATTRIBUTED] : null));
    const { unmount } = render(<Sidebar jobTitle="secretary" pathname="/dashboard" expanded showUpcoming={false} />);
    expect(await screen.findByLabelText("1 Open Items you can act on")).toBeInTheDocument();
    unmount();
    render(<Sidebar jobTitle="clinician" pathname="/dashboard" expanded showUpcoming={false} />);
    expect(await screen.findByLabelText("3 Open Items you can act on")).toBeInTheDocument();
  });
});
