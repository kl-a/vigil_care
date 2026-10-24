import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/patients/pt-1/summary", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({ ...(await importOriginal<object>()), ...api }));

import { PatientProvider } from "@/components/patients/PatientContext";
import { PatientHeader } from "@/components/patients/PatientHeader";
import { ViewerProvider } from "@/components/shell/ViewerProvider";
import { NO_MODULES } from "@/lib/modules/types";
import { ONCOLOGY_ON, userWith } from "./fixtures";

const PATIENT = {
  id: "pt-1", display_name: "Robin Sample", pseudonym: "VG-0044", history: [],
  identity: { given_name: "Robin", family_name: "Sample", dob: "1958-01-29", mrn: "1002031", address: "7 Example Cl, Parramatta NSW 2150" },
};
const PRIMARY = { id: "m-1", provider_id: "p-1", provider_name: "Dr Alex Rivera", role: "treating_oncologist", is_primary: true, is_current: true, start_date: "2024-03-01", end_date: null };
const COLORECTAL = { id: "cd-1", name: "Colorectal cancer", stage: "IIIB", cancer_status: "active", current_biomarkers: [], cancer_type: { display_name: "Colorectal cancer" } };
const MELANOMA = { id: "cd-2", name: "Melanoma, left forearm", stage: "IB", cancer_status: "no_evidence_of_disease", current_biomarkers: [], cancer_type: { display_name: "Melanoma" } };

function respond(openItems: unknown[]) {
  api.request.mockImplementation(async (path: string) => {
    if (path === "/patients/pt-1") return PATIENT;
    if (path === "/patients/pt-1/care-team") return [PRIMARY];
    if (path === "/patients/pt-1/open-items") return openItems;
    if (path === "/patients/pt-1/cancer-diagnoses") return [MELANOMA, COLORECTAL];
    return [];
  });
}

function renderHeader(modules = ONCOLOGY_ON) {
  render(
    <ViewerProvider initialUser={userWith("clinician")} loadModules={async () => modules}>
      <PatientProvider patientId="pt-1"><PatientHeader /></PatientProvider>
    </ViewerProvider>,
  );
}

describe("The Patient header band", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows who the Patient is: initials, name, Pseudonym, DOB and age, MRN, primary clinician and suburb", async () => {
    respond([]);
    renderHeader();
    const header = await screen.findByRole("region", { name: "Patient" });
    expect(await within(header).findByText("Primary:", { exact: false })).toHaveTextContent("Primary: Dr Alex Rivera");
    expect(header).toHaveTextContent("RS");
    expect(within(header).getByRole("heading", { name: "Robin Sample" })).toBeInTheDocument();
    expect(within(header).getByText("VG-0044")).toBeInTheDocument();
    expect(header).toHaveTextContent("29/01/1958 (");
    expect(header).toHaveTextContent("MRN 1002031");
    expect(header).toHaveTextContent("Parramatta NSW 2150");
    expect(header.textContent).not.toContain("7 Example Cl");
  });

  it("carries Oncology's chip for the active primary cancer, and an Open Items button when there are some", async () => {
    respond([{ type: "next_step" }, { type: "suspected_recurrence" }]);
    renderHeader();
    const header = await screen.findByRole("region", { name: "Patient" });
    expect(await within(header).findByText("Colorectal cancer · Stage IIIB (dx)")).toBeInTheDocument();
    expect(within(header).queryByText(/Melanoma/)).not.toBeInTheDocument();
    const button = await within(header).findByRole("link", { name: "2 Open Items" });
    expect(button).toHaveAttribute("href", "/patients/pt-1/summary#open-items");
    expect(button.querySelector("svg")).not.toBeNull();
  });

  it("has no cancer chip with Oncology off, and no Open Items button when there are none", async () => {
    respond([]);
    renderHeader(NO_MODULES);
    const header = await screen.findByRole("region", { name: "Patient" });
    await within(header).findByText("Primary:", { exact: false });
    expect(within(header).queryByText(/Stage/)).not.toBeInTheDocument();
    expect(within(header).queryByRole("link", { name: /Open Items/ })).not.toBeInTheDocument();
  });
});
