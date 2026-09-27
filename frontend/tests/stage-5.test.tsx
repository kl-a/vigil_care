import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));

import { Dashboard } from "@/components/dashboard/Dashboard";
import { OpenItemList } from "@/components/openItems/OpenItemList";
import { PatientProvider } from "@/components/patients/PatientContext";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { PatientSummary } from "@/components/summary/PatientSummary";
import type { OpenItem, PatientSummary as Summary } from "@/lib/summary";
import { SHIPPED_STAGE } from "@/lib/stages";
import { NO_MODULES } from "@/lib/modules/types";
import { userWith } from "./fixtures";

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

  it("lets a clinician act on each: Seen with a note, Attribute from a choice", async () => {
    const onActed = vi.fn();
    renderAs("clinician", <OpenItemList items={[DIFFERING, UNATTRIBUTED]} onActed={onActed} />);
    const differing = screen.getByText("BRAF V600E results differ").closest("li")!;
    fireEvent.change(within(differing).getByLabelText("Note (optional)"), { target: { value: "Discussed at MDT" } });
    fireEvent.click(within(differing).getByRole("button", { name: "Seen" }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith(DIFFERING.actions[0]!.path, { method: "POST", body: JSON.stringify({ note: "Discussed at MDT" }) }));
    const unattributed = screen.getByText(/not attributed/).closest("li")!;
    fireEvent.change(within(unattributed).getByLabelText("Attribute to"), { target: { value: "cd-2" } });
    await waitFor(() => expect(api.request).toHaveBeenCalledWith(UNATTRIBUTED.actions[0]!.path, { method: "POST", body: JSON.stringify({ cancer_diagnosis_id: "cd-2" }) }));
    expect(onActed).toHaveBeenCalledTimes(2);
  });

  it("asks why before ruling out, and draws each kind with its own icon and who can act", async () => {
    const recurrence: OpenItem = { ...DIFFERING, type: "suspected_recurrence", type_label: "Suspected Recurrence", icon: "alert", title: "Suspected Recurrence of Melanoma",
      actions: [{ label: "Rule out", path: "/patients/pt-1/recurrences/r-1/rule-out", input: "reason", field: null, choices: [] }] };
    renderAs("clinician", <OpenItemList items={[recurrence]} onActed={vi.fn()} />);
    const row = screen.getByText("Suspected Recurrence of Melanoma").closest("li")!;
    expect(row).toHaveTextContent("Clinician only");
    expect(row.querySelector("svg")).not.toBeNull();
    const ruleOut = within(row).getByRole("button", { name: "Rule out" });
    expect(ruleOut).toBeDisabled();
    fireEvent.change(within(row).getByLabelText("Why (rule out)"), { target: { value: "Benign on biopsy" } });
    fireEvent.click(ruleOut);
    await waitFor(() => expect(api.request).toHaveBeenCalledWith("/patients/pt-1/recurrences/r-1/rule-out", { method: "POST", body: JSON.stringify({ reason: "Benign on biopsy" }) }));
  });

  it("shows a secretary clinician-only items as 'Needs clinician', and lets them mark a Next Step done", () => {
    renderAs("secretary", <OpenItemList items={[NEXT_STEP, DIFFERING]} onActed={vi.fn()} />);
    const differing = screen.getByText("BRAF V600E results differ").closest("li")!;
    expect(within(differing).queryByRole("button", { name: "Seen" })).not.toBeInTheDocument();
    expect(differing).toHaveTextContent(/Needs clinician/);
    expect(within(screen.getByText("Discuss lung nodule at MDT").closest("li")!).getByRole("button", { name: "Mark done" })).toBeInTheDocument();
  });

  it("never offers a dismiss or snooze", () => {
    renderAs("clinician", <OpenItemList items={[NEXT_STEP, DIFFERING, UNATTRIBUTED]} onActed={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /dismiss|snooze|hide/i })).not.toBeInTheDocument();
  });
});

describe("Dashboard", () => {
  beforeEach(() => { vi.clearAllMocks(); api.request.mockImplementation(async (path: string) => (path === "/open-items" ? [NEXT_STEP, DIFFERING, UNATTRIBUTED] : undefined)); });

  it("lists the Practice's Open Items with their Patients, filtered by type and by who can act", async () => {
    renderAs("secretary", <Dashboard />);
    expect((await screen.findAllByRole("link", { name: "Robin Sample" }))[0]).toHaveAttribute("href", "/patients/pt-1/summary");
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: "Differing Biomarker Results (1)" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "All (3)" }));
    fireEvent.click(screen.getByRole("button", { name: "I can act" }));
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual([expect.stringContaining("Discuss lung nodule at MDT")]);
    fireEvent.click(screen.getByRole("button", { name: "Clinician only" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
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
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument();
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
    expect(history).toHaveTextContent("by Sam Lee (Trial coordinator)");
    expect(within(history).getByRole("link", { name: "See it in the record" })).toHaveAttribute("href", "/patients/pt-1/clinical-data?tab=conditions");
  });
});

describe("Stage 5", () => {
  it("has shipped", () => expect(SHIPPED_STAGE).toBe(5));
});
